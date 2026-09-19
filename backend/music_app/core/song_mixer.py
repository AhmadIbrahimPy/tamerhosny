"""
Song Mixer - "Sing With Tamer" duet builder.

Goal:

    For every second of the song:

        The user recorded that segment
            -> instrumental (vocal-removed) + the user's own voice

        The user did NOT record that segment
            -> the original song, untouched (Tamer's vocal + music)

    The result is a real duet: the user only replaces the exact
    seconds they actually sang, everything else stays the original
    recording.

Implementation notes:

    - Reuses AudioProcessor (ai_remix_app) so level balancing, silence
      trimming and mastering match the same quality bar as the remix
      engine instead of a naive ffmpeg `amix` chain (which quietly
      loses gain every time another input is chained in).
    - Only crossfades where the vocal source actually switches
      (Tamer's original vocal <-> the user's voice, either direction):
      the outgoing side fades down while the incoming side fades up,
      so the handoff is a smooth blend instead of a sudden cut. Joins
      between two pieces of the same source are plain concatenation -
      they're already continuous audio, nothing to blend.
    - The user's recording is time-fitted to its segment duration
      (mild time-stretch, falling back to trim/pad) since a live
      recording rarely lines up to the millisecond.
    - Every user recording gets a basic audio-engineering pass before
      it's mixed in: rumble/hiss cleanup, loudness normalization (a
      quiet phone-mic take gets brought up, a hot one gets tamed), and
      a conservative pitch nudge toward the song's own key when the
      take is clearly off (same cautious cap the remix engine uses -
      never a full "robotic" auto-tune snap).
"""

import logging
import os
import uuid

import librosa
import numpy as np
from django.conf import settings

from backend.ai_remix_app.core.audio_processor import AudioProcessor
from backend.music_app.models import SingWithTamerProject

logger = logging.getLogger(__name__)

# Maximum allowed time-stretch ratio when fitting a user recording to
# its segment duration. Beyond this, stretching would audibly distort
# the voice, so we trim/pad instead.
MAX_STRETCH_RATIO = 1.18
MIN_STRETCH_RATIO = 1.0 / MAX_STRETCH_RATIO

# Crossfade used where the vocal source actually switches (Tamer's
# original vocal <-> the user's voice). Long enough to feel like a
# deliberate handoff rather than a click; `AudioProcessor.crossfade`
# automatically shrinks this if either side is shorter.
TRANSITION_CROSSFADE_SECONDS = 0.35

# How much louder the user's voice should be than the music underneath
# it, in the seconds they're singing (RMS ratio - see
# _auto_balance_levels' own target_vocal_to_music). Tuned through a
# few rounds of direct, sometimes contradictory feedback:
#   - 1.35 (the remix engine's own default): music ducked too
#     noticeably under the vocal for a duet specifically.
#   - 1.05 (near-1:1): the reverse complaint - music read as too quiet.
#   - two flat "boost the music" multipliers on top of 1.05 (2.0, then
#     1.4) each time widened the gap back in the music's favor with
#     nothing raising the vocal to match, landing on "equal" instead of
#     the vocal clearly leading - not what was actually asked for.
# 1.4 puts the vocal clearly, audibly above the music rather than
# level with it, which is the actual relationship that was asked for.
DUET_VOCAL_TO_MUSIC_RATIO = 1.4

# Absolute level boost applied to BOTH gains together, on top of
# _auto_balance_levels' own (deliberately conservative) output - the
# music level this produces (vs DUET_VOCAL_TO_MUSIC_RATIO controlling
# the *relative* vocal/music balance above) was confirmed to sound
# right on its own.
DUET_LEVEL_BOOST = 2.0


class SongMixer:
    """Builds the final duet track for a SingWithTamerProject."""

    def __init__(self):
        self.output_dir = str(os.path.join(settings.MEDIA_ROOT, 'user_songs'))
        os.makedirs(self.output_dir, exist_ok=True)
        self.processor = AudioProcessor()

    # =========================================================
    # PUBLIC ENTRY POINT
    # =========================================================

    def create_final_song(
        self,
        project: SingWithTamerProject,
        instrumental_path: str,
        original_path: str,
    ) -> str:
        """
        Build the final duet song.

        Args:
            project: SingWithTamerProject with the user's recordings.
            instrumental_path: Path to the vocal-removed backing track.
            original_path: Path to the original song (with Tamer's vocal).

        Returns:
            Media-relative path to the final MP3.
        """
        try:
            recordings = list(
                project.lyric_recordings
                .select_related('lyric_segment')
                .order_by('lyric_segment__start_seconds')
            )

            if not recordings:
                raise ValueError("No recordings found for this project")

            sr = self.processor.sample_rate

            original, _ = self.processor.load_audio(str(original_path))
            instrumental, _ = self.processor.load_audio(str(instrumental_path))

            length = min(len(original), len(instrumental))

            if length <= 0:
                raise RuntimeError("Original or instrumental audio is empty.")

            original = original[:length]
            instrumental = instrumental[:length]

            recording_by_segment = {
                r.lyric_segment_id: r
                for r in recordings
            }

            segments = list(
                project.song.lyric_segments.all().order_by('start_seconds')
            )

            pieces = self._build_pieces(
                original=original,
                instrumental=instrumental,
                segments=segments,
                recording_by_segment=recording_by_segment,
                sr=sr,
                total_length=length,
            )

            final_mix = self._stitch_pieces(pieces, sr)

            final_mix = self.processor.normalize_and_master(final_mix)

            # =====================================================
            # EXPORT
            # =====================================================

            final_wav_path = os.path.join(
                self.output_dir,
                f"_tmp_{uuid.uuid4().hex}.wav",
            )

            self.processor.save_audio(final_mix, final_wav_path, format='wav')

            unique_id = str(uuid.uuid4())[:8]
            final_filename = f"{project.song.slug[:20]}_{unique_id}.mp3"
            final_mp3_path = os.path.join(self.output_dir, final_filename)

            self._convert_to_mp3(final_wav_path, final_mp3_path)

            os.remove(final_wav_path)

            return final_mp3_path.replace(str(settings.MEDIA_ROOT) + '/', '')

        except Exception as e:
            logger.error(f"Song mixing failed: {str(e)}")
            raise RuntimeError(f"Song mixing failed: {str(e)}")

    # =========================================================
    # BUILD TIMELINE PIECES
    # =========================================================

    def _build_pieces(
        self,
        original: np.ndarray,
        instrumental: np.ndarray,
        segments: list,
        recording_by_segment: dict,
        sr: int,
        total_length: int,
    ) -> list:
        """
        Walk the song's timeline and produce a list of
        (audio, kind) chunks, kind being "original" (untouched) or
        "duet" (instrumental + user vocal), covering every sample
        from 0 to total_length.
        """

        pieces = []
        cursor = 0

        for segment in segments:

            start_sample = max(0, int(float(segment.start_seconds) * sr))
            end_sample = min(total_length, int(float(segment.end_seconds) * sr))

            if end_sample <= start_sample:
                continue

            # Fill any gap before this segment with original audio.
            if start_sample > cursor:
                pieces.append((original[cursor:start_sample], 'original'))

            recording = recording_by_segment.get(segment.pk)

            if recording is None:
                pieces.append((original[start_sample:end_sample], 'original'))
            else:
                pieces.append((
                    self._build_duet_segment(
                        instrumental[start_sample:end_sample],
                        recording,
                        sr,
                        original[start_sample:end_sample],
                    ),
                    'duet',
                ))

            cursor = end_sample

        # Trailing audio after the last segment.
        if cursor < total_length:
            pieces.append((original[cursor:total_length], 'original'))

        if not pieces:
            pieces.append((original, 'original'))

        return pieces

    # =========================================================
    # BUILD ONE DUET SEGMENT
    # =========================================================

    def _build_duet_segment(
        self,
        instrumental_segment: np.ndarray,
        recording,
        sr: int,
        original_segment: np.ndarray,
    ) -> np.ndarray:

        seg_len = len(instrumental_segment)

        if seg_len <= 0:
            return instrumental_segment

        user_audio = self._load_user_recording(
            str(recording.audio_file.path)
        )

        # Trim dead air (mic lag before/after singing) before fitting
        # duration, so the stretch ratio reflects the actual content.
        start, end = self.processor.find_actual_start_end(user_audio)

        if end > start:
            user_audio = user_audio[start:end]

        user_audio = self._engineer_vocal(user_audio, sr)

        user_audio = self._fit_to_duration(user_audio, seg_len, sr)

        instrumental_gain, vocal_gain = (
            self.processor._auto_balance_levels(
                instrumental_segment,
                user_audio,
                target_vocal_to_music=DUET_VOCAL_TO_MUSIC_RATIO,
            )
        )

        instrumental_gain *= DUET_LEVEL_BOOST
        vocal_gain *= DUET_LEVEL_BOOST

        mixed = (
            instrumental_segment * instrumental_gain
            + user_audio * vocal_gain
        )

        # _auto_balance_levels normalizes toward its own fixed absolute
        # loudness target, independent of how loud this particular song
        # actually is - on a song mastered louder than that target, every
        # duet segment came out quieter than the untouched original
        # audio surrounding it, an audible dip each time the user's own
        # line came up. Match this segment's loudness to what the
        # original recording measures right here instead, so the duet
        # blends in at the same perceived volume as the rest of the
        # track rather than a separately-normalized level.
        mixed_rms = self.processor._measure_rms(mixed)
        reference_rms = self.processor._measure_rms(original_segment)

        if mixed_rms > 1e-7 and reference_rms > 1e-7:
            loudness_gain = float(np.clip(reference_rms / mixed_rms, 0.5, 3.0))
            mixed = mixed * loudness_gain

        peak = float(np.max(np.abs(mixed))) if mixed.size else 0.0

        if peak > 0.92:
            mixed *= (0.92 / peak)

        return mixed.astype(np.float32)

    # =========================================================
    # VOCAL AUDIO ENGINEERING
    # =========================================================

    def _engineer_vocal(
        self,
        audio: np.ndarray,
        sr: int,
    ) -> np.ndarray:
        """
        Basic audio-engineering pass on a raw phone-mic recording
        before it gets mixed into the duet:

            1. Band-limit: cut rumble/handling noise below 80Hz and
               hiss above 15kHz.
            2. Room reverb: a dry phone-mic take alone sounds
               noticeably flatter/closer than a mixed studio vocal -
               a light synthetic room tail (see _add_studio_reverb)
               gives it some of that "recorded in a booth" space
               without turning it into an obvious, distracting echo.
            3. Loudness: bring a too-quiet take up, tame a too-hot
               one, before the instrumental/vocal balance pass runs.

        A per-segment pitch "correction" toward the song's key used to
        run here too, but chroma-based key detection on a few seconds
        of solo, unaccompanied singing is unreliable enough that it was
        firing inconsistently line to line - one segment nudged up,
        the next nudged down, the next left alone - which is exactly
        what made the same voice sound noticeably thin/childlike in
        some lines and thick/muffled in others (librosa's pitch_shift
        doesn't preserve formants, so even the capped ±2 semitones this
        used to allow was audible). A short vocal line also doesn't
        really have a single "key" to correct toward in the first
        place - the mismatch this was trying to fix isn't well-defined
        for this input. Removed rather than tuned further.
        """

        if len(audio) == 0:
            return audio

        audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)

        audio = self._band_limit(audio, sr)

        audio = self._add_studio_reverb(audio, sr)

        audio = self._normalize_loudness(audio)

        return audio.astype(np.float32)

    @staticmethod
    def _add_studio_reverb(audio: np.ndarray, sr: int) -> np.ndarray:
        """
        A light synthetic room/plate reverb - not a real impulse
        response recording (no such asset bundled with this app), a
        short burst of band-limited noise shaped with an exponential
        decay stands in for one well enough at this wet level to read
        as "recorded in a space" rather than a distinct, audible echo.

        Convolution naturally extends the signal by the tail's length;
        that tail is deliberately dropped (the wet signal is trimmed
        back to the original length) rather than left to bleed into
        the next timeline piece - see _stitch_pieces, which joins
        same-kind segments with a plain concatenation that assumes
        each piece is already exactly its own duration.
        """

        from scipy import signal

        if len(audio) == 0:
            return audio

        rng = np.random.default_rng(0)  # deterministic - not aiming for per-take variation

        tail_seconds = 0.32
        tail_len = max(1, int(tail_seconds * sr))

        decay = np.exp(-np.linspace(0, 9.0, tail_len))
        impulse = rng.standard_normal(tail_len) * decay

        # Same band-limiting as the dry vocal, so the reverb tail
        # doesn't reintroduce the rumble/hiss _band_limit just removed.
        nyquist = sr / 2
        b, a = signal.butter(2, [300 / nyquist, 6000 / nyquist], btype='band')
        impulse = signal.filtfilt(b, a, impulse)

        peak = float(np.max(np.abs(impulse)))
        if peak > 1e-9:
            impulse = impulse / peak

        wet_level = 0.16  # subtle - a sense of space, not an obvious echo

        wet = np.zeros_like(audio)
        for channel in range(audio.shape[1]):
            convolved = signal.fftconvolve(audio[:, channel], impulse, mode='full')
            wet[:, channel] = convolved[:len(audio)]

        return (audio + wet * wet_level).astype(np.float32)

    @staticmethod
    def _band_limit(audio: np.ndarray, sr: int) -> np.ndarray:
        """Remove sub-80Hz rumble and above-15kHz hiss per channel."""

        from scipy import signal

        nyquist = sr / 2
        high_b, high_a = signal.butter(4, 80 / nyquist, btype='high')
        low_b, low_a = signal.butter(4, 15000 / nyquist, btype='low')

        processed = audio.copy()

        for channel in range(processed.shape[1]):
            chan = processed[:, channel]
            chan = signal.filtfilt(high_b, high_a, chan)
            chan = signal.filtfilt(low_b, low_a, chan)
            processed[:, channel] = chan

        return processed.astype(np.float32)

    def _normalize_loudness(self, audio: np.ndarray) -> np.ndarray:
        """Bring the recording to a consistent, present loudness."""

        rms = self.processor._measure_rms(audio)

        if rms <= 1e-7:
            return audio

        target_rms = 0.14

        gain = float(np.clip(target_rms / rms, 0.4, 4.0))

        audio = audio * gain

        peak = float(np.max(np.abs(audio)))

        if peak > 0.90:
            audio = audio * (0.90 / peak)

        return audio.astype(np.float32)

    # =========================================================
    # LOAD USER RECORDING
    # =========================================================

    def _load_user_recording(self, path: str) -> np.ndarray:
        """
        Load a user recording regardless of its original container.

        Browsers upload recordings in whatever format their
        MediaRecorder defaults to (webm/opus, ogg/opus, mp4/aac, ...).
        libsndfile (used by soundfile/librosa) cannot decode most of
        these directly, so we transcode through ffmpeg into a plain
        WAV first.
        """
        import subprocess
        import tempfile

        fd, wav_path = tempfile.mkstemp(suffix='.wav')
        os.close(fd)

        try:
            cmd = [
                'ffmpeg',
                '-i', path,
                '-ar', str(self.processor.sample_rate),
                '-ac', '2',
                '-y',
                wav_path,
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"Failed to decode recording '{path}': "
                    f"{result.stderr.strip()}"
                )

            audio, _ = self.processor.load_audio(wav_path)
            return audio

        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)

    # =========================================================
    # FIT USER RECORDING TO SEGMENT DURATION
    # =========================================================

    def _fit_to_duration(
        self,
        audio: np.ndarray,
        target_samples: int,
        sr: int,
    ) -> np.ndarray:

        current = len(audio)

        if current == 0:
            return np.zeros((target_samples, 2), dtype=np.float32)

        if current == target_samples:
            return audio.astype(np.float32)

        rate = current / target_samples

        clipped_rate = float(
            np.clip(rate, MIN_STRETCH_RATIO, MAX_STRETCH_RATIO)
        )

        try:
            stretched = librosa.effects.time_stretch(
                audio.T,
                rate=clipped_rate,
            ).T

            stretched = np.asarray(stretched, dtype=np.float32)

        except Exception:
            stretched = audio

        return self._pad_or_trim(stretched, target_samples)

    @staticmethod
    def _pad_or_trim(audio: np.ndarray, target_samples: int) -> np.ndarray:

        current = len(audio)

        if current == target_samples:
            return audio.astype(np.float32)

        if current > target_samples:
            return audio[:target_samples].astype(np.float32)

        channels = audio.shape[1] if audio.ndim == 2 else 2

        padding = np.zeros(
            (target_samples - current, channels),
            dtype=np.float32,
        )

        return np.concatenate([audio, padding], axis=0).astype(np.float32)

    # =========================================================
    # STITCH TIMELINE PIECES WITH CROSSFADES
    # =========================================================

    def _stitch_pieces(self, pieces: list, sr: int) -> np.ndarray:
        """
        Concatenate the timeline pieces.

        Two adjacent pieces of the SAME kind are literally consecutive
        samples of the same source audio - there is no real cut there,
        so they are joined with a plain concatenation.

        Only where the source actually switches (Tamer's original
        vocal <-> the user's voice, in either direction) do we cross-
        fade: the outgoing side fades down while the incoming side
        fades up over TRANSITION_CROSSFADE_SECONDS, so the handoff is
        a smooth blend instead of an abrupt cut.
        """

        pieces = [(audio, kind) for audio, kind in pieces if len(audio) > 0]

        if not pieces:
            return np.empty((0, 2), dtype=np.float32)

        result, prev_kind = pieces[0]

        for audio, kind in pieces[1:]:

            if kind == prev_kind:
                result = np.concatenate([result, audio], axis=0)
            else:
                result = self.processor.crossfade(
                    result,
                    audio,
                    crossfade_duration=TRANSITION_CROSSFADE_SECONDS,
                )

            prev_kind = kind

        return result.astype(np.float32)

    # =========================================================
    # EXPORT
    # =========================================================

    def _convert_to_mp3(self, input_path: str, output_path: str):
        """Convert to high-quality MP3."""
        import subprocess

        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-codec:a', 'libmp3lame',
            '-b:a', '320k',
            '-y',
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"MP3 conversion failed: {result.stderr}")
