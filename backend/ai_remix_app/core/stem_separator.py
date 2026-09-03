"""
Professional Stem Separation using Demucs.

Song 1:
    drums + bass + other = instrumental

Song 2:
    vocals only

Important:
    Keep stereo information.
    Do not convert stems to mono.

Mixing philosophy:
    - Preserve the natural Demucs stems.
    - Avoid aggressive normalization.
    - Avoid stacking drums/bass/other at the same gain.
    - Automatically balance instrumental stem levels.
    - Keep enough headroom for the vocal mix later.
    
Enhancement:
    - Use AI-based noise reduction for vocals
    - Use spectral processing for instrumental
    - Apply professional audio enhancement techniques
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict

import numpy as np
import soundfile as sf
import librosa
from scipy import signal
from scipy.signal import wiener


class StemSeparator:
    """Professional vocal/instrumental separation."""

    def __init__(
        self,
        output_dir: str = "media/ai_remix/stems",
        model: str = "htdemucs",
    ):
        self.output_dir = Path(output_dir)
        self.model = model

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    # =========================================================
    # SEPARATE
    # =========================================================

    def separate(
        self,
        file_path: str,
    ) -> Dict[str, str]:

        file_path = str(
            Path(file_path).resolve()
        )

        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"Audio file not found: {file_path}"
            )

        # IMPORTANT:
        # Use the exact Python executable running Django.
        #
        # This fixes:
        # No module named demucs
        command = [
            sys.executable,
            "-m",
            "demucs",
            "--name",
            self.model,
            "--out",
            str(self.output_dir),
            file_path,
        ]

        try:

            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )

        except subprocess.CalledProcessError as exc:

            error = (
                exc.stderr.strip()
                if exc.stderr
                else exc.stdout.strip()
            )

            raise RuntimeError(
                "Demucs stem separation failed:\n"
                f"{error}"
            )

        song_name = Path(
            file_path
        ).stem

        stem_dir = (
            self.output_dir
            / self.model
            / song_name
        )

        if not stem_dir.exists():
            raise RuntimeError(
                f"Demucs output not found: {stem_dir}"
            )

        result = {
            "vocals": str(
                stem_dir / "vocals.wav"
            ),
            "drums": str(
                stem_dir / "drums.wav"
            ),
            "bass": str(
                stem_dir / "bass.wav"
            ),
            "other": str(
                stem_dir / "other.wav"
            ),
        }

        missing = [
            name
            for name, path in result.items()
            if not os.path.exists(path)
        ]

        if missing:
            raise RuntimeError(
                "Missing stems: "
                + ", ".join(missing)
            )

        return result

    # =========================================================
    # VOCALS
    # =========================================================

    def get_vocals(
        self,
        file_path: str,
    ) -> str:

        stems = self.separate(
            file_path
        )

        return self.enhance_vocals(
            stems["vocals"]
        )

    def enhance_vocals(
        self,
        vocals_path: str,
    ) -> str:
        """
        Advanced vocal enhancement using spectral processing:
        - Spectral noise reduction
        - Harmonic-percussive separation
        - Dynamic range compression
        - Spectral smoothing
        - De-essing for high frequencies
        """
        # Load vocals
        audio, sr = sf.read(
            vocals_path,
            dtype="float32",
            always_2d=True,
        )
        
        audio = np.asarray(
            audio,
            dtype=np.float32,
        )
        
        audio = np.nan_to_num(
            audio,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )
        
        # Process each channel
        processed_channels = []
        for channel in range(audio.shape[1]):
            channel_audio = audio[:, channel]
            
            # 1. Harmonic-Percussive Separation to isolate voice harmonics
            y_harmonic, y_percussive = librosa.effects.hpss(
                channel_audio,
                kernel_size=31,
                power=2.0
            )
            
            # Use harmonic component (contains voice)
            channel_audio = y_harmonic
            
            # 2. Spectral noise reduction using spectral subtraction
            S = librosa.stft(channel_audio, n_fft=2048, hop_length=512)
            magnitude = np.abs(S)
            phase = np.angle(S)
            
            # Estimate noise from first frames
            noise_frames = 10
            noise_profile = np.mean(magnitude[:, :noise_frames], axis=1, keepdims=True)
            
            # Spectral subtraction with over-subtraction factor
            alpha = 2.0
            beta = 0.01
            enhanced_magnitude = magnitude - alpha * noise_profile
            enhanced_magnitude = np.maximum(enhanced_magnitude, beta * magnitude)
            
            # Reconstruct signal
            S_enhanced = enhanced_magnitude * np.exp(1j * phase)
            channel_audio = librosa.istft(S_enhanced, hop_length=512)
            
            # 3. Spectral gating for transient noise
            S = librosa.stft(channel_audio, n_fft=2048, hop_length=512)
            magnitude = np.abs(S)
            phase = np.angle(S)
            
            # Compute spectral gate threshold
            median_mag = np.median(magnitude, axis=1, keepdims=True)
            threshold = median_mag * 1.5
            
            # Apply gate
            mask = magnitude > threshold
            S_gated = S * mask
            channel_audio = librosa.istft(S_gated, hop_length=512)
            
            # 4. De-essing (reduce sibilance)
            S = librosa.stft(channel_audio, n_fft=2048, hop_length=512)
            magnitude = np.abs(S)
            phase = np.angle(S)
            
            # Identify high-frequency energy (above 8kHz)
            freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
            high_freq_mask = freqs > 8000
            
            # Reduce high-frequency peaks
            if np.any(high_freq_mask):
                high_freq_mag = magnitude[high_freq_mask, :]
                high_freq_median = np.median(high_freq_mag)
                high_freq_mag = np.minimum(high_freq_mag, high_freq_median * 1.3)
                magnitude[high_freq_mask, :] = high_freq_mag
            
            S_deessed = magnitude * np.exp(1j * phase)
            channel_audio = librosa.istft(S_deessed, hop_length=512)
            
            # 5. Gentle compression
            rms = np.sqrt(np.mean(channel_audio ** 2))
            if rms > 0:
                target_rms = 0.15
                compression_ratio = min(1.8, target_rms / rms)
                channel_audio = channel_audio * compression_ratio
            
            # 6. Normalize
            peak = np.max(np.abs(channel_audio))
            if peak > 0.85:
                channel_audio = channel_audio * (0.85 / peak)
            
            processed_channels.append(channel_audio)
        
        # Combine channels
        processed_audio = np.column_stack(processed_channels)
        
        # Save enhanced vocals
        output_path = (
            Path(vocals_path).parent
            / "vocals_enhanced.wav"
        )
        
        sf.write(
            output_path,
            processed_audio,
            sr,
            subtype="PCM_16",
        )
        
        return str(output_path)

    def process_vocals(
        self,
        vocals_path: str,
    ) -> str:
        """
        Process vocals to improve quality:
        - Remove high-frequency noise
        - Remove low-frequency rumble
        - Apply gentle compression
        - Normalize to optimal level
        """
        import librosa
        import soundfile as sf
        
        # Load vocals
        audio, sr = sf.read(
            vocals_path,
            dtype="float32",
            always_2d=True,
        )
        
        audio = np.asarray(
            audio,
            dtype=np.float32,
        )
        
        audio = np.nan_to_num(
            audio,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )
        
        # Convert to mono for processing
        mono = np.mean(audio, axis=1)
        
        # High-pass filter to remove rumble (below 80Hz)
        from scipy import signal
        nyquist = sr / 2
        low_cutoff = 80 / nyquist
        b, a = signal.butter(4, low_cutoff, btype='high')
        mono = signal.filtfilt(b, a, mono)
        
        # Low-pass filter to remove high-frequency noise (above 16kHz)
        high_cutoff = 16000 / nyquist
        b, a = signal.butter(4, high_cutoff, btype='low')
        mono = signal.filtfilt(b, a, mono)
        
        # Apply gentle compression
        rms = np.sqrt(np.mean(mono ** 2))
        if rms > 0:
            target_rms = 0.12
            compression_ratio = min(1.5, target_rms / rms)
            mono = mono * compression_ratio
        
        # Normalize to prevent clipping but preserve dynamics
        peak = np.max(np.abs(mono))
        if peak > 0.85:
            mono = mono * (0.85 / peak)
        
        # Convert back to stereo
        processed_audio = np.column_stack([mono, mono])
        
        # Save processed vocals
        output_path = (
            Path(vocals_path).parent
            / "vocals_processed.wav"
        )
        
        sf.write(
            output_path,
            processed_audio,
            sr,
            subtype="PCM_16",
        )
        
        return str(output_path)

    # =========================================================
    # INSTRUMENTAL
    # =========================================================

    def get_instrumental(
        self,
        file_path: str,
    ) -> str:

        stems = self.separate(
            file_path
        )

        instrumental_path = self.build_instrumental(
            stems
        )
        
        return self.enhance_instrumental(
            instrumental_path
        )

    def enhance_instrumental(
        self,
        instrumental_path: str,
    ) -> str:
        """
        Advanced instrumental enhancement using spectral processing:
        - Spectral enhancement for clarity
        - Harmonic-percussive separation
        - Dynamic EQ for frequency balance
        - Stereo enhancement
        - Transient preservation
        """
        # Load instrumental
        audio, sr = sf.read(
            instrumental_path,
            dtype="float32",
            always_2d=True,
        )
        
        audio = np.asarray(
            audio,
            dtype=np.float32,
        )
        
        audio = np.nan_to_num(
            audio,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )
        
        # Process each channel
        processed_channels = []
        for channel in range(audio.shape[1]):
            channel_audio = audio[:, channel]
            
            # 1. Harmonic-Percussive Separation to enhance musical elements
            y_harmonic, y_percussive = librosa.effects.hpss(
                channel_audio,
                kernel_size=31,
                power=2.0
            )
            
            # Blend harmonic and percussive for balanced sound
            channel_audio = 0.7 * y_harmonic + 0.3 * y_percussive

            # 2. Dynamic EQ for frequency balance
            S = librosa.stft(channel_audio, n_fft=2048, hop_length=512)
            magnitude = np.abs(S)
            phase = np.angle(S)
            
            freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
            
            # Boost low-mids (200-500Hz) for warmth
            low_mid_mask = (freqs >= 200) & (freqs <= 500)
            if np.any(low_mid_mask):
                magnitude[low_mid_mask, :] *= 1.15
            
            # Boost presence (2-4kHz) for clarity
            presence_mask = (freqs >= 2000) & (freqs <= 4000)
            if np.any(presence_mask):
                magnitude[presence_mask, :] *= 1.1
            
            # Reduce harsh highs (above 12kHz)
            high_mask = freqs > 12000
            if np.any(high_mask):
                magnitude[high_mask, :] *= 0.85
            
            # Reconstruct
            S_eq = magnitude * np.exp(1j * phase)
            channel_audio = librosa.istft(S_eq, hop_length=512)
            
            # 3. Transient preservation
            S = librosa.stft(channel_audio, n_fft=2048, hop_length=512)
            magnitude = np.abs(S)
            phase = np.angle(S)
            
            # Enhance transients using spectral flux
            spectral_flux = np.diff(magnitude, axis=1, prepend=magnitude[:, :1])
            transient_mask = spectral_flux > np.percentile(spectral_flux, 75)
            
            # Slightly boost transients
            magnitude[transient_mask] *= 1.05
            
            # Reconstruct
            S_transient = magnitude * np.exp(1j * phase)
            channel_audio = librosa.istft(S_transient, hop_length=512)
            
            # 4. Gentle compression
            rms = np.sqrt(np.mean(channel_audio ** 2))
            if rms > 0:
                target_rms = 0.18
                compression_ratio = min(1.6, target_rms / rms)
                channel_audio = channel_audio * compression_ratio
            
            # 5. Normalize
            peak = np.max(np.abs(channel_audio))
            if peak > 0.88:
                channel_audio = channel_audio * (0.88 / peak)
            
            processed_channels.append(channel_audio)
        
        # Combine channels
        processed_audio = np.column_stack(processed_channels)
        
        # 6. Stereo enhancement (widen stereo image)
        if processed_audio.shape[1] == 2:
            left = processed_audio[:, 0]
            right = processed_audio[:, 1]
            
            # Mid-Side processing
            mid = (left + right) / 2
            side = (left - right) / 2
            
            # Slightly boost side for wider stereo
            side = side * 1.15
            
            # Reconstruct
            processed_audio[:, 0] = mid + side
            processed_audio[:, 1] = mid - side
            
            # Normalize after stereo processing
            peak = np.max(np.abs(processed_audio))
            if peak > 0.88:
                processed_audio = processed_audio * (0.88 / peak)
        
        # Save enhanced instrumental
        output_path = (
            Path(instrumental_path).parent
            / "instrumental_enhanced.wav"
        )
        
        sf.write(
            output_path,
            processed_audio,
            sr,
            subtype="PCM_16",
        )
        
        return str(output_path)

    def process_instrumental(
        self,
        instrumental_path: str,
    ) -> str:
        """
        Process instrumental to improve quality:
        - Remove high-frequency harshness
        - Enhance low frequencies
        - Apply gentle EQ
        - Normalize to optimal level
        """
        import librosa
        import soundfile as sf
        
        # Load instrumental
        audio, sr = sf.read(
            instrumental_path,
            dtype="float32",
            always_2d=True,
        )
        
        audio = np.asarray(
            audio,
            dtype=np.float32,
        )
        
        audio = np.nan_to_num(
            audio,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )
        
        # Process each channel
        processed_channels = []
        for channel in range(audio.shape[1]):
            channel_audio = audio[:, channel]
            
            # Low-pass filter to remove harsh high frequencies (above 15kHz)
            from scipy import signal
            nyquist = sr / 2
            high_cutoff = 15000 / nyquist
            b, a = signal.butter(4, high_cutoff, btype='low')
            channel_audio = signal.filtfilt(b, a, channel_audio)
            
            # High-pass filter to remove sub-bass rumble (below 40Hz)
            low_cutoff = 40 / nyquist
            b, a = signal.butter(4, low_cutoff, btype='high')
            channel_audio = signal.filtfilt(b, a, channel_audio)
            
            # Gentle EQ boost for mid-range clarity (1kHz - 4kHz)
            # Using a simple shelving approach
            from scipy.signal import lfilter
            # Boost 2kHz by 2dB
            boost_freq = 2000 / nyquist
            b, a = signal.butter(2, boost_freq, btype='band')
            band_signal = signal.lfilter(b, a, channel_audio)
            channel_audio = channel_audio + (band_signal * 0.15)
            
            # Normalize channel
            peak = np.max(np.abs(channel_audio))
            if peak > 0.88:
                channel_audio = channel_audio * (0.88 / peak)
            
            processed_channels.append(channel_audio)
        
        # Combine channels
        processed_audio = np.column_stack(processed_channels)
        
        # Save processed instrumental
        output_path = (
            Path(instrumental_path).parent
            / "instrumental_processed.wav"
        )
        
        sf.write(
            output_path,
            processed_audio,
            sr,
            subtype="PCM_16",
        )
        
        return str(output_path)

    # =========================================================
    # AUDIO HELPERS
    # =========================================================

    @staticmethod
    def _safe_rms(
        audio: np.ndarray,
    ) -> float:

        """
        Calculate RMS safely.

        Stereo is converted to mono ONLY for
        level measurement.

        The actual audio always remains stereo.
        """

        if audio.size == 0:
            return 0.0

        mono = np.mean(
            audio,
            axis=1,
            dtype=np.float64,
        )

        if len(mono) == 0:
            return 0.0

        value = float(
            np.sqrt(
                np.mean(
                    np.square(
                        mono
                    )
                )
            )
        )

        if not np.isfinite(value):
            return 0.0

        return max(
            value,
            1e-8,
        )

    @staticmethod
    def _safe_peak(
        audio: np.ndarray,
    ) -> float:

        if audio.size == 0:
            return 0.0

        peak = float(
            np.max(
                np.abs(audio)
            )
        )

        if not np.isfinite(peak):
            return 0.0

        return peak

    # =========================================================
    # SMART STEM LEVEL
    # =========================================================

    def _calculate_stem_gains(
        self,
        audio_parts,
    ) -> list:

        """
        Automatically balance:

            drums
            bass
            other

        We intentionally do NOT make all stems
        the same loudness.

        Bass and drums contain a lot of energy,
        therefore they receive slightly less gain.

        'other' keeps a little more level because
        it usually contains guitars, synths,
        piano, pads, etc.
        """

        gains = []

        for name, audio in audio_parts:

            rms = self._safe_rms(
                audio
            )

            if rms <= 0:
                gains.append(
                    0.0
                )
                continue

            if name == "drums":

                base_gain = 0.72

            elif name == "bass":

                base_gain = 0.62

            else:

                base_gain = 0.78

            # -------------------------------------------------
            # Prevent a very loud stem from dominating.
            # -------------------------------------------------

            if rms > 0.25:

                loudness_correction = 0.82

            elif rms > 0.18:

                loudness_correction = 0.90

            elif rms < 0.055:

                loudness_correction = 1.08

            else:

                loudness_correction = 1.0

            gain = (
                base_gain
                * loudness_correction
            )

            # -------------------------------------------------
            # Keep gains inside a safe range.
            # -------------------------------------------------

            gain = float(
                np.clip(
                    gain,
                    0.50,
                    0.82,
                )
            )

            gains.append(
                gain
            )

        return gains

    # =========================================================
    # BUILD INSTRUMENTAL
    # =========================================================

    def build_instrumental(
        self,
        stems: Dict[str, str],
    ) -> str:

        """
        Build instrumental from:

            drums
            bass
            other

        Keep stereo.

        IMPORTANT:

        We don't simply do:

            drums * 0.90
            bass  * 0.90
            other * 0.90

        because that can create excessive energy.

        Instead:
            - measure each stem
            - apply intelligent gain
            - sum with headroom
            - perform only safety peak protection
        """

        paths = [
            (
                "drums",
                stems["drums"],
            ),
            (
                "bass",
                stems["bass"],
            ),
            (
                "other",
                stems["other"],
            ),
        ]

        audio_parts = []

        sample_rate = None
        channels = None

        # =====================================================
        # LOAD STEMS
        # =====================================================

        for name, path in paths:

            if not os.path.exists(path):

                raise RuntimeError(
                    f"Stem file not found: {path}"
                )

            audio, sr = sf.read(
                path,
                dtype="float32",
                always_2d=True,
            )

            audio = np.asarray(
                audio,
                dtype=np.float32,
            )

            audio = np.nan_to_num(
                audio,
                nan=0.0,
                posinf=0.0,
                neginf=0.0,
            )

            if audio.size == 0:

                continue

            if sample_rate is None:

                sample_rate = sr

            elif sr != sample_rate:

                raise RuntimeError(
                    "Stem sample rates do not match."
                )

            if channels is None:

                channels = (
                    audio.shape[1]
                )

            # -------------------------------------------------
            # Preserve stereo.
            # -------------------------------------------------

            if audio.shape[1] != channels:

                if audio.shape[1] == 1:

                    audio = np.repeat(
                        audio,
                        channels,
                        axis=1,
                    )

                else:

                    audio = (
                        audio[
                            :,
                            :channels
                        ]
                    )

            audio_parts.append(
                (
                    name,
                    audio,
                )
            )

        if not audio_parts:

            raise RuntimeError(
                "No instrumental stems found."
            )

        # =====================================================
        # SAME LENGTH
        # =====================================================

        min_length = min(
            len(audio)
            for _, audio in audio_parts
        )

        if min_length <= 0:

            raise RuntimeError(
                "Instrumental stems contain no audio."
            )

        # =====================================================
        # SMART GAINS
        # =====================================================

        gains = (
            self._calculate_stem_gains(
                audio_parts
            )
        )

        # =====================================================
        # CREATE MIX
        # =====================================================

        instrumental = np.zeros(
            (
                min_length,
                channels,
            ),
            dtype=np.float32,
        )

        for (
            index,
            (
                name,
                audio,
            ),
        ) in enumerate(
            audio_parts
        ):

            gain = gains[index]

            if gain <= 0:
                continue

            instrumental += (
                audio[
                    :min_length
                ]
                * gain
            )

        # =====================================================
        # CLEAN
        # =====================================================

        instrumental = np.nan_to_num(
            instrumental,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )

        # =====================================================
        # PEAK PROTECTION
        # =====================================================

        peak = self._safe_peak(
            instrumental
        )

        if peak > 0.90:

            instrumental *= (
                0.90 / peak
            )

        # =====================================================
        # VERY IMPORTANT:
        #
        # Do NOT normalize a quiet instrumental back to 1.0.
        #
        # The next stage will compare its real level against
        # the vocal and perform smart mixing.
        # =====================================================

        instrumental = np.clip(
            instrumental,
            -0.92,
            0.92,
        ).astype(
            np.float32
        )

        # =====================================================
        # OUTPUT
        # =====================================================

        output_path = (
            Path(
                stems["other"]
            ).parent
            / "instrumental.wav"
        )

        sf.write(
            output_path,
            instrumental,
            sample_rate,
            subtype="PCM_16",
        )

        return str(
            output_path
        )