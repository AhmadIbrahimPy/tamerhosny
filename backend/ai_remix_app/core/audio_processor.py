"""
Intelligent Music Remix Engine

Goal:

Song 1:
    Instrumental / background music

Song 2:
    Vocals

Result:
    Song 1 instrumental
    +
    Song 2 vocals

Important design decisions:

- Preserve stereo.
- Do NOT automatically pitch-shift vocals.
- Do NOT tile vocals repeatedly.
- Do NOT mix original Song 2 with its vocal stem.
- Use time-stretch only for BPM.
- Short intro.
- Short crossfades.
- Keep vocal natural.
- Automatically balance vocal and instrumental levels.
"""

import os
from typing import List, Tuple

import librosa
import numpy as np
import soundfile as sf

from pedalboard import (
    Pedalboard,
    Compressor,
    Limiter,
    HighpassFilter,
)

from .stem_separator import StemSeparator


class AudioProcessor:
    """Core audio analysis and processing."""

    SAMPLE_RATE = 44100

    KEYS = [
        "C",
        "C#",
        "D",
        "D#",
        "E",
        "F",
        "F#",
        "G",
        "G#",
        "A",
        "A#",
        "B",
    ]

    MAJOR_PROFILE = np.array([
        6.35, 2.23, 3.48, 2.33,
        4.38, 4.09, 2.52, 5.19,
        2.39, 3.66, 2.29, 2.88
    ])

    MINOR_PROFILE = np.array([
        6.33, 2.68, 3.52, 5.38,
        2.60, 3.53, 2.54, 4.75,
        3.98, 2.69, 3.34, 3.17
    ])

    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
    ):
        self.sample_rate = sample_rate

    # =========================================================
    # AUDIO SHAPE
    # =========================================================

    @staticmethod
    def _to_stereo(
        audio: np.ndarray,
    ) -> np.ndarray:

        audio = np.asarray(
            audio,
            dtype=np.float32,
        )

        if audio.ndim == 1:

            return np.column_stack(
                [audio, audio]
            )

        if audio.ndim == 2:

            # soundfile:
            # samples x channels

            if audio.shape[1] == 1:

                return np.repeat(
                    audio,
                    2,
                    axis=1,
                )

            if audio.shape[1] >= 2:

                return audio[:, :2]

        raise ValueError(
            "Unsupported audio shape."
        )

    @staticmethod
    def _to_mono(
        audio: np.ndarray,
    ) -> np.ndarray:

        audio = np.asarray(
            audio,
            dtype=np.float32,
        )

        if audio.ndim == 1:
            return audio

        return np.mean(
            audio,
            axis=1,
        ).astype(
            np.float32
        )

    # =========================================================
    # LOAD / SAVE
    # =========================================================

    def load_audio(
        self,
        file_path: str,
    ) -> Tuple[np.ndarray, int]:

        try:

            y, sr = librosa.load(
                file_path,
                sr=self.sample_rate,
                mono=False,
            )

            y = np.asarray(
                y,
                dtype=np.float32,
            )

            if y.size == 0:

                raise ValueError(
                    "Audio file is empty."
                )

            # librosa stereo shape:
            # channels x samples

            if y.ndim == 2:

                y = np.transpose(y)

            y = self._to_stereo(y)

            y = np.nan_to_num(
                y,
                nan=0.0,
                posinf=0.0,
                neginf=0.0,
            )

            return y, sr

        except Exception as exc:

            raise RuntimeError(
                f"Error loading audio file: {exc}"
            )

    def save_audio(
        self,
        audio_data: np.ndarray,
        output_path: str,
        format: str = "wav",
    ):

        directory = os.path.dirname(
            output_path
        )

        if directory:

            os.makedirs(
                directory,
                exist_ok=True,
            )

        audio_data = np.asarray(
            audio_data,
            dtype=np.float32,
        )

        audio_data = np.nan_to_num(
            audio_data,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )

        sf.write(
            output_path,
            audio_data,
            self.sample_rate,
            format=format,
        )

    # =========================================================
    # ANALYSIS
    # =========================================================

    def analyze_audio(
        self,
        audio_data: np.ndarray,
    ) -> dict:

        mono = self._to_mono(
            audio_data
        )

        if len(mono) == 0:

            return {
                "bpm": 120.0,
                "key": "C",
                "mode": "major",
                "duration": 0.0,
                "beats": [],
                "downbeats": [],
                "onsets": [],
                "energy": 0.0,
                "sections": [],
            }

        duration = (
            len(mono)
            / self.sample_rate
        )

        if len(mono) < self.sample_rate:

            return {
                "bpm": 120.0,
                "key": "C",
                "mode": "major",
                "duration": float(duration),
                "beats": [],
                "downbeats": [],
                "onsets": [],
                "energy": 0.0,
                "sections": [],
            }

        # -----------------------------------------------------
        # BPM
        # -----------------------------------------------------

        tempo, beat_frames = (
            librosa.beat.beat_track(
                y=mono,
                sr=self.sample_rate,
                units="frames",
            )
        )

        if isinstance(
            tempo,
            np.ndarray,
        ):

            tempo = float(
                np.mean(tempo)
            )

        else:

            tempo = float(tempo)

        if (
            tempo <= 0
            or not np.isfinite(tempo)
        ):

            tempo = 120.0

        beat_times = (
            librosa.frames_to_time(
                beat_frames,
                sr=self.sample_rate,
            )
        )

        # -----------------------------------------------------
        # ONSETS
        # -----------------------------------------------------

        onset_frames = (
            librosa.onset.onset_detect(
                y=mono,
                sr=self.sample_rate,
                backtrack=True,
            )
        )

        onset_times = (
            librosa.frames_to_time(
                onset_frames,
                sr=self.sample_rate,
            )
        )

        # -----------------------------------------------------
        # DOWNBEATS
        # -----------------------------------------------------

        downbeat_times = (
            self._detect_downbeats(
                beat_times
            )
        )

        # -----------------------------------------------------
        # KEY
        # -----------------------------------------------------

        key, mode = (
            self._detect_key_and_mode(
                mono
            )
        )

        # -----------------------------------------------------
        # ENERGY
        # -----------------------------------------------------

        rms = librosa.feature.rms(
            y=mono,
            frame_length=4096,
            hop_length=1024,
        )[0]

        energy = (
            float(np.mean(rms))
            if len(rms)
            else 0.0
        )

        sections = (
            self._detect_sections(
                mono,
                beat_times,
                tempo,
            )
        )

        return {
            "bpm": tempo,
            "key": key,
            "mode": mode,
            "duration": float(duration),
            "beats": beat_times.tolist(),
            "downbeats": downbeat_times.tolist(),
            "onsets": onset_times.tolist(),
            "energy": energy,
            "sections": sections,
        }

    # =========================================================
    # KEY
    # =========================================================

    def _detect_key_and_mode(
        self,
        audio_data: np.ndarray,
    ) -> Tuple[str, str]:

        try:

            chroma = (
                librosa.feature.chroma_cqt(
                    y=audio_data,
                    sr=self.sample_rate,
                )
            )

            chroma_mean = np.mean(
                chroma,
                axis=1,
            )

            norm = np.linalg.norm(
                chroma_mean
            )

            if norm <= 0:

                return "C", "major"

            chroma_mean /= norm

            best_score = -np.inf
            best_key = "C"
            best_mode = "major"

            major_profile = (
                self.MAJOR_PROFILE
                / np.linalg.norm(
                    self.MAJOR_PROFILE
                )
            )

            minor_profile = (
                self.MINOR_PROFILE
                / np.linalg.norm(
                    self.MINOR_PROFILE
                )
            )

            for i, key in enumerate(
                self.KEYS
            ):

                rotated = np.roll(
                    chroma_mean,
                    -i,
                )

                major_score = np.corrcoef(
                    rotated,
                    major_profile,
                )[0, 1]

                minor_score = np.corrcoef(
                    rotated,
                    minor_profile,
                )[0, 1]

                if major_score > best_score:

                    best_score = major_score
                    best_key = key
                    best_mode = "major"

                if minor_score > best_score:

                    best_score = minor_score
                    best_key = key
                    best_mode = "minor"

            return (
                best_key,
                best_mode,
            )

        except Exception:

            return "C", "major"

    # =========================================================
    # DOWNBEATS
    # =========================================================

    def _detect_downbeats(
        self,
        beat_times: np.ndarray,
    ) -> np.ndarray:

        if len(beat_times) == 0:

            return np.array([])

        return beat_times[::4]

    # =========================================================
    # SECTIONS
    # =========================================================

    def _detect_sections(
        self,
        audio_data: np.ndarray,
        beat_times: np.ndarray,
        tempo: float,
    ) -> List[dict]:

        duration = (
            len(audio_data)
            / self.sample_rate
        )

        if duration <= 0:

            return []

        seconds_per_beat = (
            60.0
            / max(tempo, 1.0)
        )

        bar_duration = (
            seconds_per_beat * 4
        )

        section_duration = (
            bar_duration * 4
        )

        section_duration = float(
            np.clip(
                section_duration,
                6.0,
                14.0,
            )
        )

        sections = []

        rms = librosa.feature.rms(
            y=audio_data,
            frame_length=4096,
            hop_length=1024,
        )[0]

        frame_times = (
            librosa.frames_to_time(
                np.arange(len(rms)),
                sr=self.sample_rate,
                hop_length=1024,
            )
        )

        global_max = (
            float(np.max(rms))
            if len(rms)
            else 1.0
        )

        start = 0.0

        while start < duration:

            end = min(
                duration,
                start + section_duration,
            )

            mask = (
                (frame_times >= start)
                &
                (frame_times < end)
            )

            if np.any(mask):

                section_energy = float(
                    np.mean(
                        rms[mask]
                    )
                )

            else:

                section_energy = 0.0

            normalized_energy = (
                section_energy
                / max(
                    global_max,
                    1e-8,
                )
            )

            sections.append({
                "start": float(start),
                "end": float(end),
                "duration": float(
                    end - start
                ),
                "energy": float(
                    normalized_energy
                ),
                "type": (
                    self._classify_section(
                        normalized_energy
                    )
                ),
            })

            start = end

        return sections

    def _classify_section(
        self,
        energy: float,
    ) -> str:

        if energy < 0.20:

            return "intro_or_break"

        if energy < 0.40:

            return "verse"

        if energy < 0.65:

            return "build"

        return "chorus_or_drop"

    # =========================================================
    # BPM
    # =========================================================

    def _harmonize_bpm(
        self,
        target_bpm: float,
        source_bpm: float,
    ) -> float:

        target_bpm = (
            float(target_bpm)
            if target_bpm > 0
            else 120.0
        )

        source_bpm = (
            float(source_bpm)
            if source_bpm > 0
            else 120.0
        )

        candidates = [
            source_bpm,
            source_bpm * 2,
            source_bpm / 2,
        ]

        return float(
            min(
                candidates,
                key=lambda x:
                abs(x - target_bpm),
            )
        )

    def change_tempo(
        self,
        audio_data: np.ndarray,
        original_bpm: float,
        target_bpm: float,
    ) -> np.ndarray:

        if (
            original_bpm <= 0
            or target_bpm <= 0
        ):

            return audio_data

        rate = (
            target_bpm
            / original_bpm
        )

        # Prevent extreme stretching.

        rate = float(
            np.clip(
                rate,
                0.92,
                1.08,
            )
        )

        if abs(rate - 1.0) < 0.015:

            return audio_data

        try:

            result = (
                librosa.effects.time_stretch(
                    audio_data.T,
                    rate=rate,
                )
            )

            return (
                result.T
                .astype(np.float32)
            )

        except Exception:

            return audio_data

    # =========================================================
    # KEY MATCHING
    # =========================================================

    def match_key(
        self,
        audio_data: np.ndarray,
        current_key: str,
        target_key: str,
        current_mode: str = "major",
        target_mode: str = "major",
    ) -> np.ndarray:

        """
        Conservative key matching.

        Automatic pitch shifting is avoided unless a target key
        is explicitly requested.
        """

        if not current_key or not target_key:

            return audio_data

        if current_key == target_key:

            return audio_data

        key_to_semitone = {
            key: index
            for index, key in enumerate(
                self.KEYS
            )
        }

        current = key_to_semitone.get(
            current_key
        )

        target = key_to_semitone.get(
            target_key
        )

        if (
            current is None
            or target is None
        ):

            return audio_data

        steps = target - current

        if steps > 6:

            steps -= 12

        elif steps < -6:

            steps += 12

        # Never make a large automatic shift.

        if abs(steps) > 2:

            return audio_data

        if steps == 0:

            return audio_data

        try:

            result = (
                librosa.effects.pitch_shift(
                    audio_data.T,
                    sr=self.sample_rate,
                    n_steps=steps,
                )
            )

            return (
                result.T
                .astype(np.float32)
            )

        except Exception:

            return audio_data

    # =========================================================
    # ACTUAL START / END
    # =========================================================

    def find_actual_start(
        self,
        audio_data: np.ndarray,
    ) -> int:

        mono = self._to_mono(
            audio_data
        )

        if len(mono) == 0:

            return 0

        try:

            _, index = (
                librosa.effects.trim(
                    mono,
                    top_db=40,
                )
            )

            return int(index[0])

        except Exception:

            return 0

    def find_actual_end(
        self,
        audio_data: np.ndarray,
    ) -> int:

        mono = self._to_mono(
            audio_data
        )

        if len(mono) == 0:

            return 0

        try:

            _, index = (
                librosa.effects.trim(
                    mono,
                    top_db=40,
                )
            )

            return int(index[1])

        except Exception:

            return len(mono)

    # =========================================================
    # SLICE
    # =========================================================

    def _safe_slice(
        self,
        audio: np.ndarray,
        start: float,
        end: float,
    ) -> np.ndarray:

        start_sample = max(
            0,
            int(
                start
                * self.sample_rate
            ),
        )

        end_sample = min(
            len(audio),
            int(
                end
                * self.sample_rate
            ),
        )

        if end_sample <= start_sample:

            return np.empty(
                (0, 2),
                dtype=np.float32,
            )

        return (
            audio[
                start_sample:end_sample
            ]
            .astype(np.float32)
        )

    # =========================================================
    # CROSSFADE
    # =========================================================

    def crossfade(
        self,
        audio1: np.ndarray,
        audio2: np.ndarray,
        crossfade_duration: float = 1.0,
    ) -> np.ndarray:

        if len(audio1) == 0:

            return audio2

        if len(audio2) == 0:

            return audio1

        samples = int(
            crossfade_duration
            * self.sample_rate
        )

        samples = min(
            samples,
            len(audio1) // 2,
            len(audio2) // 2,
        )

        if samples <= 0:

            return np.concatenate(
                [audio1, audio2],
                axis=0,
            )

        x = np.linspace(
            0,
            1,
            samples,
            dtype=np.float32,
        )

        fade_out = np.cos(
            x * np.pi / 2
        )[:, None]

        fade_in = np.sin(
            x * np.pi / 2
        )[:, None]

        overlap = (
            audio1[-samples:]
            * fade_out
            +
            audio2[:samples]
            * fade_in
        )

        result = np.concatenate(
            [
                audio1[:-samples],
                overlap,
                audio2[samples:],
            ],
            axis=0,
        )

        return result.astype(
            np.float32
        )

    # =========================================================
    # GAIN
    # =========================================================

    def apply_gain(
        self,
        audio: np.ndarray,
        gain: float,
    ) -> np.ndarray:

        return (
            audio
            * float(gain)
        ).astype(
            np.float32
        )

    # =========================================================
    # AUTO LEVEL ANALYSIS
    # =========================================================

    def _measure_rms(
        self,
        audio: np.ndarray,
    ) -> float:

        """
        Measure perceived average level using RMS.

        We use the median of frame RMS values instead of the
        maximum so one loud kick or vocal peak doesn't affect
        the whole balance.
        """

        if len(audio) == 0:

            return 0.0

        mono = self._to_mono(
            audio
        )

        if len(mono) == 0:

            return 0.0

        try:

            rms = librosa.feature.rms(
                y=mono,
                frame_length=4096,
                hop_length=1024,
            )[0]

            if len(rms) == 0:

                return 0.0

            # Ignore complete silence.

            active = rms[
                rms > np.max(rms) * 0.03
            ]

            if len(active) == 0:

                active = rms

            return float(
                np.median(active)
            )

        except Exception:

            value = np.sqrt(
                np.mean(
                    mono ** 2
                )
            )

            return float(value)

    def _auto_balance_levels(
        self,
        instrumental: np.ndarray,
        vocal: np.ndarray,
    ) -> Tuple[float, float]:

        """
        Automatically balance instrumental and vocal.

        Target:
            Vocal should normally be slightly louder than
            the instrumental.

        Behavior:

            Music too loud:
                reduce music.

            Music too quiet:
                increase music.

            Vocal too loud:
                reduce vocal.

            Vocal too quiet:
                increase vocal.

        The correction is intentionally limited so the system
        cannot suddenly make either stem extremely loud.

        Returns:
            instrumental_gain,
            vocal_gain
        """

        instrumental_rms = (
            self._measure_rms(
                instrumental
            )
        )

        vocal_rms = (
            self._measure_rms(
                vocal
            )
        )

        # -----------------------------------------------------
        # No useful measurement.
        # -----------------------------------------------------

        if (
            instrumental_rms <= 1e-7
            and vocal_rms <= 1e-7
        ):

            return 0.68, 0.82

        if instrumental_rms <= 1e-7:

            return 0.0, 0.82

        if vocal_rms <= 1e-7:

            return 0.68, 0.0

        # -----------------------------------------------------
        # Desired relationship.
        #
        # Vocal is normally around 1.35x the RMS of the
        # instrumental.
        #
        # This does NOT mean 1.35x louder perceptually in dB.
        # It simply keeps the vocal clearly present.
        # -----------------------------------------------------

        target_vocal_to_music = 1.35

        current_ratio = (
            vocal_rms
            / max(
                instrumental_rms,
                1e-8,
            )
        )

        # -----------------------------------------------------
        # Start from conservative base levels.
        # -----------------------------------------------------

        base_gain = 0.80

        # -----------------------------------------------------
        # Correct the relationship symmetrically.
        #
        # If vocal is too quiet:
        #   vocal gain goes up
        #   music gain goes down slightly
        #
        # If vocal is too loud:
        #   vocal gain goes down
        #   music gain goes up slightly
        #
        # Using sqrt keeps the correction balanced.
        # -----------------------------------------------------

        ratio_correction = (
            target_vocal_to_music
            / max(
                current_ratio,
                0.05,
            )
        )

        ratio_correction = float(
            np.clip(
                ratio_correction,
                0.50,
                2.00,
            )
        )

        vocal_gain = (
            base_gain
            * np.sqrt(
                ratio_correction
            )
        )

        instrumental_gain = (
            base_gain
            / np.sqrt(
                ratio_correction
            )
        )

        # -----------------------------------------------------
        # Absolute level correction.
        #
        # If both stems are very quiet, allow them to come up.
        # If both are already loud, keep them down.
        #
        # This prevents the situation where the relative ratio
        # is correct but the whole remix is unnecessarily quiet.
        # -----------------------------------------------------

        combined_rms = np.sqrt(
            (
                instrumental_rms ** 2
                +
                vocal_rms ** 2
            )
            / 2.0
        )

        target_combined_rms = 0.115

        if combined_rms > 1e-7:

            overall_gain = (
                target_combined_rms
                / combined_rms
            )

        else:

            overall_gain = 1.0

        # Keep automatic level correction conservative.

        overall_gain = float(
            np.clip(
                overall_gain,
                0.70,
                1.25,
            )
        )

        instrumental_gain *= (
            overall_gain
        )

        vocal_gain *= (
            overall_gain
        )

        # -----------------------------------------------------
        # Final safety limits.
        #
        # Never allow automatic balancing to apply extreme
        # gain changes.
        # -----------------------------------------------------

        instrumental_gain = float(
            np.clip(
                instrumental_gain,
                0.45,
                1.15,
            )
        )

        vocal_gain = float(
            np.clip(
                vocal_gain,
                0.55,
                1.25,
            )
        )

        return (
            instrumental_gain,
            vocal_gain,
        )

    # =========================================================
    # FADE
    # =========================================================

    def fade_in(
        self,
        audio: np.ndarray,
        duration: float,
    ) -> np.ndarray:

        if len(audio) == 0:

            return audio

        samples = min(
            int(
                duration
                * self.sample_rate
            ),
            len(audio),
        )

        if samples <= 0:

            return audio

        curve = np.linspace(
            0.0,
            1.0,
            samples,
            dtype=np.float32,
        )[:, None]

        result = audio.copy()

        result[:samples] *= curve

        return result

    def fade_out(
        self,
        audio: np.ndarray,
        duration: float,
    ) -> np.ndarray:

        if len(audio) == 0:

            return audio

        samples = min(
            int(
                duration
                * self.sample_rate
            ),
            len(audio),
        )

        if samples <= 0:

            return audio

        curve = np.linspace(
            1.0,
            0.0,
            samples,
            dtype=np.float32,
        )[:, None]

        result = audio.copy()

        result[-samples:] *= curve

        return result

    # =========================================================
    # MASTER
    # =========================================================

    def normalize_and_master(
        self,
        audio_data: np.ndarray,
    ) -> np.ndarray:

        if len(audio_data) == 0:

            return audio_data

        audio_data = np.asarray(
            audio_data,
            dtype=np.float32,
        )

        audio_data = np.nan_to_num(
            audio_data,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )

        peak = float(
            np.max(
                np.abs(audio_data)
            )
        )

        if peak > 0.95:

            audio_data *= (
                0.95 / peak
            )

        # Gentle mastering only.

        board = Pedalboard([
            HighpassFilter(
                cutoff_frequency_hz=28
            ),

            Compressor(
                threshold_db=-18,
                ratio=1.5,
                attack_ms=20,
                release_ms=150,
            ),

            Limiter(
                threshold_db=-1.0
            ),
        ])

        try:

            processed = board(
                audio_data,
                self.sample_rate,
            )

            processed = np.asarray(
                processed,
                dtype=np.float32,
            )

        except Exception:

            processed = audio_data

        peak = float(
            np.max(
                np.abs(processed)
            )
        )

        if peak > 0.95:

            processed *= (
                0.95 / peak
            )

        return np.clip(
            processed,
            -0.95,
            0.95,
        ).astype(
            np.float32
        )


class AIRemixGenerator:
    """
    AI Music Remix.

    Song 1:
        instrumental

    Song 2:
        vocals

    Final:
        Song 1 instrumental
        +
        Song 2 vocals
    """

    def __init__(self):

        self.processor = (
            AudioProcessor()
        )

        self.separator = (
            StemSeparator()
        )

    # =========================================================
    # VOCAL PREPARATION
    # =========================================================

    def _prepare_vocal(
        self,
        vocal: np.ndarray,
    ) -> np.ndarray:

        """
        Clean vocal without changing its character.

        No EQ that makes it thin.
        No aggressive compression.
        No pitch shifting.
        """

        vocal = np.asarray(
            vocal,
            dtype=np.float32,
        )

        vocal = np.nan_to_num(
            vocal,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )

        peak = float(
            np.max(
                np.abs(vocal)
            )
        )

        if peak > 0.90:

            vocal *= (
                0.90 / peak
            )

        return vocal

    # =========================================================
    # BUILD INTRO
    # =========================================================

    def _build_intro(
        self,
        instrumental: np.ndarray,
        analysis: dict,
    ) -> np.ndarray:

        sr = self.processor.sample_rate

        if len(instrumental) == 0:

            return np.empty(
                (0, 2),
                dtype=np.float32,
            )

        bpm = float(
            analysis.get(
                "bpm",
                120.0,
            )
            or 120.0
        )

        # -----------------------------------------------------
        # Intro = 4 bars
        # -----------------------------------------------------

        beat_duration = (
            60.0 / bpm
        )

        intro_duration = (
            beat_duration * 16
        )

        intro_duration = float(
            np.clip(
                intro_duration,
                6.0,
                10.0,
            )
        )

        intro_samples = min(
            int(
                intro_duration
                * sr
            ),
            len(instrumental),
        )

        if intro_samples <= 0:

            return np.empty(
                (0, 2),
                dtype=np.float32,
            )

        intro = (
            instrumental[
                :intro_samples
            ].copy()
        )

        fade_in_samples = min(
            int(0.15 * sr),
            len(intro),
        )

        if fade_in_samples > 0:

            intro[
                :fade_in_samples
            ] *= np.linspace(
                0.0,
                1.0,
                fade_in_samples,
                dtype=np.float32,
            )[:, None]

        return intro.astype(
            np.float32
        )

    # =========================================================
    # BUILD MASHUP
    # =========================================================

    def _build_mashup(
        self,
        instrumental: np.ndarray,
        vocal: np.ndarray,
    ) -> np.ndarray:

        """
        Core mashup.

        The instrumental and vocal are automatically balanced
        based on their actual RMS levels.

        We do NOT simply use fixed values such as:

            instrumental *= 0.68
            vocal *= 0.82

        because every song has a different recording level.

        Instead:

            loud music  -> automatically reduced
            quiet music -> automatically increased

            loud vocal  -> automatically reduced
            quiet vocal -> automatically increased

        The correction is conservative to keep the result natural.
        """

        # -----------------------------------------------------
        # Use the longest available background.
        #
        # Vocal is never repeated.
        # -----------------------------------------------------

        if len(instrumental) == 0:

            return vocal.astype(
                np.float32
            )

        if len(vocal) == 0:

            return instrumental.astype(
                np.float32
            )

        length = min(
            len(instrumental),
            len(vocal),
        )

        instrumental = (
            instrumental[:length]
            .copy()
        )

        vocal = (
            vocal[:length]
            .copy()
        )

        # -----------------------------------------------------
        # AUTO BALANCE
        # -----------------------------------------------------

        (
            instrumental_gain,
            vocal_gain,
        ) = (
            self.processor
            ._auto_balance_levels(
                instrumental,
                vocal,
            )
        )

        instrumental *= (
            instrumental_gain
        )

        vocal *= (
            vocal_gain
        )

        # -----------------------------------------------------
        # MIX
        # -----------------------------------------------------

        mix = (
            instrumental
            + vocal
        )

        # -----------------------------------------------------
        # Peak protection.
        # -----------------------------------------------------

        peak = float(
            np.max(
                np.abs(mix)
            )
        )

        if peak > 0.92:

            mix *= (
                0.92 / peak
            )

        return mix.astype(
            np.float32
        )

    # =========================================================
    # BUILD OUTRO
    # =========================================================

    def _build_outro(
        self,
        instrumental: np.ndarray,
        vocal: np.ndarray,
    ) -> np.ndarray:

        sr = (
            self.processor.sample_rate
        )

        if len(instrumental) == 0:

            return np.empty(
                (0, 2),
                dtype=np.float32,
            )

        if len(vocal) == 0:

            outro_duration = min(
                6.0,
                len(instrumental) / sr,
            )

        else:

            outro_duration = min(
                6.0,
                len(instrumental) / sr,
                len(vocal) / sr,
            )

        samples = int(
            outro_duration * sr
        )

        if samples <= 0:

            return np.empty(
                (0, 2),
                dtype=np.float32,
            )

        instrumental_part = (
            instrumental[-samples:]
            .copy()
        )

        if len(vocal):

            vocal_part = (
                vocal[-samples:]
                .copy()
            )

        else:

            vocal_part = np.zeros_like(
                instrumental_part
            )

        # -----------------------------------------------------
        # Balance outro using the same automatic system.
        # -----------------------------------------------------

        (
            instrumental_gain,
            vocal_gain,
        ) = (
            self.processor
            ._auto_balance_levels(
                instrumental_part,
                vocal_part,
            )
        )

        instrumental_part *= (
            instrumental_gain
        )

        vocal_part *= (
            vocal_gain
        )

        # Vocal leaves first.

        vocal_part = (
            self.processor.fade_out(
                vocal_part,
                2.5,
            )
        )

        outro = (
            instrumental_part
            + vocal_part
        )

        # Then music ends.

        outro = (
            self.processor.fade_out(
                outro,
                3.0,
            )
        )

        return outro.astype(
            np.float32
        )

    # =========================================================
    # MAIN
    # =========================================================

    def generate_remix(
        self,
        sources: List[dict],
        target_config: dict,
    ) -> np.ndarray:

        if not sources:

            raise ValueError(
                "No audio sources provided."
            )

        # =====================================================
        # ONE SONG
        # =====================================================

        if len(sources) == 1:

            audio, _ = (
                self.processor.load_audio(
                    sources[0]["file_path"]
                )
            )

            return (
                self.processor
                .normalize_and_master(
                    audio
                )
            )

        # =====================================================
        # TWO SONGS
        # =====================================================

        song1_path = (
            sources[0]["file_path"]
        )

        song2_path = (
            sources[1]["file_path"]
        )

        # =====================================================
        # DEMUCS
        # =====================================================

        stems1 = (
            self.separator.separate(
                song1_path
            )
        )

        stems2 = (
            self.separator.separate(
                song2_path
            )
        )

        # Song 1 = instrumental

        instrumental1_path = (
            self.separator
            .build_instrumental(
                stems1
            )
        )

        # Song 2 = vocal only

        vocals2_path = (
            stems2["vocals"]
        )

        # =====================================================
        # LOAD
        # =====================================================

        instrumental1, _ = (
            self.processor.load_audio(
                instrumental1_path
            )
        )

        vocals2, _ = (
            self.processor.load_audio(
                vocals2_path
            )
        )

        # =====================================================
        # ANALYSIS
        # =====================================================

        analysis1 = (
            self.processor.analyze_audio(
                instrumental1
            )
        )

        analysis2 = (
            self.processor.analyze_audio(
                vocals2
            )
        )

        # =====================================================
        # BPM
        # =====================================================

        requested_bpm = (
            target_config.get(
                "target_bpm"
            )
            if target_config
            else None
        )

        target_bpm = (
            float(requested_bpm)
            if requested_bpm
            else float(
                analysis1["bpm"]
            )
        )

        source2_bpm = (
            self.processor
            ._harmonize_bpm(
                target_bpm,
                analysis2["bpm"],
            )
        )

        # -----------------------------------------------------
        # Song 1 background
        # -----------------------------------------------------

        if abs(
            analysis1["bpm"]
            - target_bpm
        ) > 2:

            instrumental1 = (
                self.processor.change_tempo(
                    instrumental1,
                    analysis1["bpm"],
                    target_bpm,
                )
            )

        # -----------------------------------------------------
        # Song 2 vocal
        #
        # Tempo only.
        #
        # No pitch shift.
        # -----------------------------------------------------

        if abs(
            source2_bpm
            - target_bpm
        ) > 2:

            vocals2 = (
                self.processor.change_tempo(
                    vocals2,
                    source2_bpm,
                    target_bpm,
                )
            )

        # =====================================================
        # KEY
        # =====================================================

        requested_key = (
            target_config.get(
                "target_key"
            )
            if target_config
            else None
        )

        if requested_key:

            vocals2 = (
                self.processor.match_key(
                    vocals2,
                    analysis2["key"],
                    requested_key,
                    analysis2.get(
                        "mode",
                        "major",
                    ),
                    analysis1.get(
                        "mode",
                        "major",
                    ),
                )
            )

        # =====================================================
        # CLEAN VOCAL SILENCE
        # =====================================================

        vocal_start = (
            self.processor
            .find_actual_start(
                vocals2
            )
        )

        vocal_end = (
            self.processor
            .find_actual_end(
                vocals2
            )
        )

        if vocal_end > vocal_start:

            vocals2 = vocals2[
                vocal_start:vocal_end
            ]

        # =====================================================
        # PREPARE VOCAL
        # =====================================================

        vocals2 = (
            self._prepare_vocal(
                vocals2
            )
        )

        # =====================================================
        # MATCH LENGTH
        # =====================================================

        instrumental_duration = (
            len(instrumental1)
            / self.processor.sample_rate
        )

        vocal_duration = (
            len(vocals2)
            / self.processor.sample_rate
        )

        # -----------------------------------------------------
        # Never repeat vocal.
        #
        # If vocal is longer than instrumental:
        # trim vocal.
        #
        # If vocal is shorter:
        # keep the available vocal only.
        # -----------------------------------------------------

        if (
            vocal_duration
            > instrumental_duration
        ):

            vocals2 = vocals2[
                :len(instrumental1)
            ]

        # =====================================================
        # INTRO
        # =====================================================

        intro = (
            self._build_intro(
                instrumental1,
                analysis1,
            )
        )

        # =====================================================
        # MAIN
        # =====================================================

        main = (
            self._build_mashup(
                instrumental1,
                vocals2,
            )
        )

        # =====================================================
        # OUTRO
        # =====================================================

        outro = (
            self._build_outro(
                instrumental1,
                vocals2,
            )
        )

        # =====================================================
        # ASSEMBLE
        # =====================================================

        final_mix = intro

        # -----------------------------------------------------
        # Intro -> Main
        # -----------------------------------------------------

        if len(main):

            final_mix = (
                self.processor.crossfade(
                    final_mix,
                    main,
                    crossfade_duration=1.0,
                )
            )

        # -----------------------------------------------------
        # Main -> Outro
        # -----------------------------------------------------

        if len(outro):

            final_mix = (
                self.processor.crossfade(
                    final_mix,
                    outro,
                    crossfade_duration=1.0,
                )
            )

        # =====================================================
        # FINAL SAFETY
        # =====================================================

        final_mix = np.nan_to_num(
            final_mix,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )

        peak = float(
            np.max(
                np.abs(final_mix)
            )
        )

        if peak > 0.94:

            final_mix *= (
                0.94 / peak
            )

        # =====================================================
        # MASTER
        # =====================================================

        final_mix = (
            self.processor
            .normalize_and_master(
                final_mix
            )
        )

        return final_mix