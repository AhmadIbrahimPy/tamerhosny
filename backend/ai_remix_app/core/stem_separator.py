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
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict

import numpy as np
import soundfile as sf


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

        return stems["vocals"]

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

        return self.build_instrumental(
            stems
        )

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