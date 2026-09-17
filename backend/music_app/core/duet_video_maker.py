"""Builds a short, shareable vertical (mobile) video for a completed
"Sing With Tamer" duet: the song's own cover art as a slowly zooming
background, with the user's and Tamer's photos as two pulsing circular
avatars over it, set to the duet's final mixed audio.

Deliberately simple (as asked for) - no waveform/lyrics sync, no
narration, just enough motion that it doesn't look like a static image
when shared as a video on a phone.
"""
import logging
import math
import os
import subprocess
import tempfile
import threading
import uuid

from django.conf import settings

logger = logging.getLogger(__name__)

# Vertical, mobile-native (Stories/Reels/Shorts) - 9:16.
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30

AVATAR_SIZE = 520
AVATAR_BORDER = 14
AVATAR_BORDER_COLOR = (212, 175, 55, 255)  # matches the site's --accent gold
AVATAR_FALLBACK_BG = (34, 38, 58, 255)
AVATAR_SILHOUETTE = (90, 96, 128, 255)

# "Logo sting": the brand's name falling into place letter by letter,
# then a white flash/pop, that opens the video (over a black screen)
# and then recurs periodically over the live background so a clip
# stays identifiable as ours even if someone reposts a middle section.
STING_FONT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'assets', 'fonts', 'Anton-Regular.ttf',
)
STING_TEXT = 'TAMER HOSNY'
STING_FONT_SIZE = 130
STING_BIG_FONT_SIZE = int(STING_FONT_SIZE * 1.35)
STING_COLOR = '0xD4AF37'  # matches AVATAR_BORDER_COLOR gold
STING_LETTER_STAGGER = 0.06  # seconds between each letter starting its fall
STING_FALL_DURATION = 0.45  # seconds for one letter to fall into place
STING_PAUSE_BEFORE_FLASH = 0.15
STING_FLASH_DURATION = 0.35
STING_PERIOD_SECONDS = 20  # how often the sting repeats over the live video
STING_MIN_TAIL_SECONDS = 1.0  # don't start a repeat too close to the very end

WATERMARK_TEXT = 'TAMERHOSNY.COM'
WATERMARK_FONT_SIZE = 32


class DuetVideoMaker:

    def __init__(self):
        self.output_dir = os.path.join(settings.MEDIA_ROOT, 'duet_videos')
        os.makedirs(self.output_dir, exist_ok=True)

    # =====================================================
    # PUBLIC ENTRY POINT
    # =====================================================

    def create_video(self, project, progress_callback=None) -> str:
        """Returns the media-relative path to the finished mp4.
        progress_callback(percent), if given, is called from this same
        thread as ffmpeg's own encode progress comes in (0-99 - the
        caller decides what "100" means, once this has actually returned).
        """
        with tempfile.TemporaryDirectory(prefix='duet_video_') as tmp_dir:
            background_path = self._resolve_background(project, tmp_dir)
            user_avatar_path = self._build_avatar(
                self._resolve_local_path(getattr(project.user, 'profile_image', None), tmp_dir),
                os.path.join(tmp_dir, 'user_avatar.png'),
            )
            tamer_avatar_path = self._build_avatar(
                self._resolve_tamer_photo(tmp_dir),
                os.path.join(tmp_dir, 'tamer_avatar.png'),
            )

            audio_path = project.final_audio_file.path
            duration = self._probe_duration(audio_path)
            frame_count = max(1, int(duration * VIDEO_FPS))

            sting_frames_dir, _ = self._render_sting_frames(tmp_dir)
            watermark_path = self._render_watermark_image(os.path.join(tmp_dir, 'watermark.png'))

            unique_id = uuid.uuid4().hex[:10]
            filename = f"{project.song.slug[:20]}_{unique_id}.mp4"
            output_path = os.path.join(self.output_dir, filename)

            self._render(
                background_path=background_path,
                tamer_avatar_path=tamer_avatar_path,
                user_avatar_path=user_avatar_path,
                audio_path=audio_path,
                duration=duration,
                frame_count=frame_count,
                sting_frames_dir=sting_frames_dir,
                watermark_path=watermark_path,
                output_path=output_path,
                progress_callback=progress_callback,
            )

            return output_path.replace(str(settings.MEDIA_ROOT) + '/', '')

    # =====================================================
    # ASSET RESOLUTION
    # =====================================================

    @staticmethod
    def _resolve_local_path(field_file, tmp_dir):
        """A Django FieldFile that's actually on local disk - None if
        unset. (Duet avatars are always local ImageFields in this app,
        never a remote URL, so no download branch is needed here.)
        """
        if not field_file:
            return None
        try:
            path = field_file.path
        except (ValueError, NotImplementedError):
            return None
        return path if os.path.exists(path) else None

    def _resolve_tamer_photo(self, tmp_dir):
        from backend.people_app.models import Person

        tamer = Person.objects.filter(slug='tamer-hosny').first()
        if tamer and tamer.profile_image:
            return self._resolve_local_path(tamer.profile_image, tmp_dir)
        return None

    def _resolve_background(self, project, tmp_dir):
        """The song's cover, as a local file ffmpeg can read directly.
        Falls back to downloading an external cover URL, then to a
        plain gradient card if there's truly nothing to show.
        """
        song = project.song

        if song.cover_image:
            path = self._resolve_local_path(song.cover_image, tmp_dir)
            if path:
                return path

        if song.album_id and song.album.cover_image:
            path = self._resolve_local_path(song.album.cover_image, tmp_dir)
            if path:
                return path

        cover_url = song.display_cover_url
        if cover_url and cover_url.startswith('http'):
            downloaded = self._download_image(cover_url, os.path.join(tmp_dir, 'bg_downloaded.jpg'))
            if downloaded:
                return downloaded

        return self._make_fallback_background(os.path.join(tmp_dir, 'bg_fallback.jpg'))

    @staticmethod
    def _download_image(url, dest_path):
        import requests

        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            with open(dest_path, 'wb') as f:
                f.write(response.content)
            return dest_path
        except Exception as e:
            logger.warning('Duet video: failed to download cover image %s: %s', url, e)
            return None

    @staticmethod
    def _make_fallback_background(dest_path):
        from PIL import Image

        img = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT), (18, 16, 28))
        img.save(dest_path, quality=90)
        return dest_path

    # =====================================================
    # AVATAR (circular, bordered) BUILDING
    # =====================================================

    def _build_avatar(self, source_path, dest_path):
        from PIL import Image, ImageDraw, ImageOps

        size = AVATAR_SIZE
        canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))

        if source_path:
            try:
                photo = Image.open(source_path).convert('RGB')
                photo = ImageOps.fit(photo, (size, size), Image.LANCZOS)
                canvas.paste(photo, (0, 0))
            except Exception as e:
                logger.warning('Duet video: failed to load avatar %s: %s', source_path, e)
                self._draw_silhouette(canvas, size)
        else:
            self._draw_silhouette(canvas, size)

        mask = Image.new('L', (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        circular = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        circular.paste(canvas, (0, 0), mask)

        draw = ImageDraw.Draw(circular)
        inset = AVATAR_BORDER / 2
        draw.ellipse(
            (inset, inset, size - inset, size - inset),
            outline=AVATAR_BORDER_COLOR, width=AVATAR_BORDER,
        )

        circular.save(dest_path)
        return dest_path

    @staticmethod
    def _draw_silhouette(canvas, size):
        """No real photo to show - a plain generic-person shape instead
        of leaving it blank or risking a missing-font crash from trying
        to draw initials text.
        """
        from PIL import ImageDraw

        draw = ImageDraw.Draw(canvas)
        draw.rectangle((0, 0, size, size), fill=AVATAR_FALLBACK_BG)
        head_r = size * 0.17
        cx, cy = size / 2, size * 0.38
        draw.ellipse((cx - head_r, cy - head_r, cx + head_r, cy + head_r), fill=AVATAR_SILHOUETTE)
        shoulder_w = size * 0.62
        shoulder_h = size * 0.5
        sx0, sy0 = (size - shoulder_w) / 2, size * 0.56
        draw.ellipse((sx0, sy0, sx0 + shoulder_w, sy0 + shoulder_h), fill=AVATAR_SILHOUETTE)

    # =====================================================
    # PROBE + RENDER
    # =====================================================

    @staticmethod
    def _probe_duration(audio_path) -> float:
        result = subprocess.run(
            [
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', audio_path,
            ],
            capture_output=True, text=True, timeout=30,
        )
        try:
            duration = float(result.stdout.strip())
        except (TypeError, ValueError):
            duration = 0.0
        return duration if duration > 0 else 30.0

    # =====================================================
    # LOGO STING (intro + periodic "TAMER HOSNY" animation)
    # =====================================================

    @staticmethod
    def _sting_letter_geometry():
        """x position (in the final frame) for each non-space character
        of STING_TEXT, centered as a whole word - measured once with
        the real font metrics rather than guessed/hard-coded widths.
        """
        from PIL import ImageFont

        font = ImageFont.truetype(STING_FONT_PATH, STING_FONT_SIZE)
        widths = [font.getlength(ch) for ch in STING_TEXT]
        total_width = sum(widths)
        start_x = (VIDEO_WIDTH - total_width) / 2

        letters = []
        cursor = start_x
        for ch, width in zip(STING_TEXT, widths):
            if ch != ' ':
                letters.append((ch, cursor))
            cursor += width
        return letters

    def _sting_occurrences(self, duration):
        """Absolute start times (seconds) the sting plays at: always at
        t=0 (the intro, over black), then every STING_PERIOD_SECONDS
        over the live video for as long as the clip has room left.
        """
        assemble_end = (len(STING_TEXT) - 1) * STING_LETTER_STAGGER + STING_FALL_DURATION
        sting_total = assemble_end + STING_PAUSE_BEFORE_FLASH + STING_FLASH_DURATION

        occurrences = [0.0]
        next_start = STING_PERIOD_SECONDS
        while next_start + sting_total + STING_MIN_TAIL_SECONDS <= duration:
            occurrences.append(next_start)
            next_start += STING_PERIOD_SECONDS
        return occurrences, sting_total

    @staticmethod
    def _sting_timing():
        """(flash_start, flash_end) in seconds, relative to one sting's
        own start - shared by the frame renderer and the occurrence
        scheduler so they can never drift apart.
        """
        assemble_end = (len(STING_TEXT) - 1) * STING_LETTER_STAGGER + STING_FALL_DURATION
        flash_start = assemble_end + STING_PAUSE_BEFORE_FLASH
        flash_end = flash_start + STING_FLASH_DURATION
        return flash_start, flash_end

    def _sting_occurrences(self, duration):
        """Absolute start times (seconds) the sting plays at: always at
        t=0 (the intro, over black), then every STING_PERIOD_SECONDS
        over the live video for as long as the clip has room left.
        """
        _, sting_total = self._sting_timing()

        occurrences = [0.0]
        next_start = STING_PERIOD_SECONDS
        while next_start + sting_total + STING_MIN_TAIL_SECONDS <= duration:
            occurrences.append(next_start)
            next_start += STING_PERIOD_SECONDS
        return occurrences

    def _render_sting_frames(self, tmp_dir):
        """Pre-renders the falling-letters + white-flash "logo sting" as
        a short RGBA PNG sequence with Pillow (not ffmpeg's drawtext -
        not every ffmpeg build ships with libfreetype). Reused at every
        occurrence in the real render via tpad (to shift it in time) +
        overlay, so the exact same clip plays over black in the intro
        and over the live video on every later repeat.
        """
        from PIL import Image, ImageDraw, ImageFont

        letters = self._sting_letter_geometry()
        flash_start, flash_end = self._sting_timing()

        font = ImageFont.truetype(STING_FONT_PATH, STING_FONT_SIZE)
        big_font = ImageFont.truetype(STING_FONT_PATH, STING_BIG_FONT_SIZE)
        big_word_x = (VIDEO_WIDTH - big_font.getlength(STING_TEXT)) / 2
        big_word_y = VIDEO_HEIGHT / 2 - STING_BIG_FONT_SIZE / 2

        start_y = -(STING_FONT_SIZE * 1.5)
        target_y = VIDEO_HEIGHT / 2 - STING_FONT_SIZE / 2

        frames_dir = os.path.join(tmp_dir, 'sting_frames')
        os.makedirs(frames_dir, exist_ok=True)
        # A couple of frames past flash_end, so the clip's last frame is
        # guaranteed fully transparent - overlay repeats that last frame
        # forever past the clip's end, so it must never be a visible one.
        frame_count = max(1, int(math.ceil(flash_end * VIDEO_FPS)) + 2)

        for frame_index in range(frame_count):
            t = frame_index / VIDEO_FPS
            canvas = Image.new('RGBA', (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))

            if t < flash_start:
                # Letters falling into place, one by one, then sitting
                # assembled (their eased fraction just stays at 1) until
                # the flash below takes over.
                draw = ImageDraw.Draw(canvas)
                for letter_index, (ch, x) in enumerate(letters):
                    letter_start = letter_index * STING_LETTER_STAGGER
                    if t < letter_start:
                        continue
                    fraction = min(1.0, (t - letter_start) / STING_FALL_DURATION)
                    eased = 1 - (1 - fraction) ** 3
                    y = start_y + (target_y - start_y) * eased
                    draw.text(
                        (x, y), ch, font=font, fill=(212, 175, 55, 255),
                        stroke_width=4, stroke_fill=(0, 0, 0, 255),
                    )
            else:
                # The assembled word "pops" bigger, fading out as the
                # flash below peaks, so nothing lingers once it's over.
                word_alpha = int(255 * (1 - min(1.0, (t - flash_start) / STING_FLASH_DURATION)))
                if word_alpha > 0:
                    word_layer = Image.new('RGBA', (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
                    ImageDraw.Draw(word_layer).text(
                        (big_word_x, big_word_y), STING_TEXT, font=big_font,
                        fill=(212, 175, 55, word_alpha), stroke_width=5, stroke_fill=(0, 0, 0, word_alpha),
                    )
                    canvas = Image.alpha_composite(canvas, word_layer)

            if t >= flash_start:
                # A white bloom that peaks exactly halfway through the
                # flash window - that's also the instant the real render
                # swaps the black intro background for the live video,
                # so the swap itself is hidden inside the brightest point.
                u = min(1.0, (t - flash_start) / STING_FLASH_DURATION)
                flash_alpha = int(255 * 0.9 * math.sin(math.pi * u))
                if flash_alpha > 0:
                    flash_layer = Image.new('RGBA', (VIDEO_WIDTH, VIDEO_HEIGHT), (255, 255, 255, flash_alpha))
                    canvas = Image.alpha_composite(canvas, flash_layer)

            canvas.save(os.path.join(frames_dir, f'frame_{frame_index:05d}.png'))

        return frames_dir, frame_count

    def _render_watermark_image(self, dest_path):
        """A static, full-frame, mostly-transparent PNG with just the
        domain name near the bottom - looped as its own input and
        overlaid for the whole video (once the intro sting reveals it).
        """
        from PIL import Image, ImageDraw, ImageFont

        canvas = Image.new('RGBA', (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
        font = ImageFont.truetype(STING_FONT_PATH, WATERMARK_FONT_SIZE)
        x = (VIDEO_WIDTH - font.getlength(WATERMARK_TEXT)) / 2
        y = VIDEO_HEIGHT * 0.9
        ImageDraw.Draw(canvas).text(
            (x, y), WATERMARK_TEXT, font=font, fill=(255, 255, 255, 166),
            stroke_width=2, stroke_fill=(0, 0, 0, 115),
        )
        canvas.save(dest_path)
        return dest_path

    def _build_sting_filters(self, input_label, output_label, duration, sting_input_index, watermark_input_index):
        """Chains the black-screen intro mask, the persistent domain
        watermark, and the pre-rendered "logo sting" clip (shifted, via
        tpad, to every occurrence) onto the given filter label. Returns
        the filter_complex fragment (ending in output_label).
        """
        occurrences = self._sting_occurrences(duration)
        flash_start, _ = self._sting_timing()
        reveal_t = flash_start + STING_FLASH_DURATION / 2  # mid-flash: the swap is hidden by the white

        parts = [
            f"[{sting_input_index}:v]format=rgba[stingsrc]",
            f"[{watermark_input_index}:v]format=rgba[wm]",
        ]

        branch_labels = [f'[st{i}]' for i in range(len(occurrences))]
        parts.append(f"[stingsrc]split={len(occurrences)}{''.join(branch_labels)}")

        for occ_index, occ_start in enumerate(occurrences):
            parts.append(
                f"{branch_labels[occ_index]}tpad=start_duration={occ_start:.3f}:"
                f"start_mode=add:color=black@0.0[stp{occ_index}]"
            )

        cur = input_label

        # Intro only: solid black over everything (bg + avatars) until
        # the sting's flash is at its brightest, so the real background
        # only ever appears "revealed" by the flash, never as a visible cut.
        parts.append(
            f"{cur}drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:"
            f"enable='lt(t,{reveal_t:.3f})'[vblk]"
        )
        cur = '[vblk]'

        parts.append(f"{cur}[wm]overlay=enable='gte(t,{reveal_t:.3f})'[vwm]")
        cur = '[vwm]'

        for occ_index in range(len(occurrences)):
            nxt = f'[vst{occ_index}]'
            parts.append(f"{cur}[stp{occ_index}]overlay{nxt}")
            cur = nxt

        parts[-1] = parts[-1][: -len(cur)] + output_label
        return ';'.join(parts)

    def _render(
        self, background_path, tamer_avatar_path, user_avatar_path,
        audio_path, duration, frame_count, sting_frames_dir,
        watermark_path, output_path, progress_callback=None,
    ):
        # Gentle continuous zoom-in on the cover, capped so it never
        # blows past a modest crop; each avatar pulses on its own
        # slightly offset cycle so they don't breathe in perfect unison.
        filter_complex = (
            f"[0:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
            f"zoompan=z='min(zoom+0.0006,1.22)':d={frame_count}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={VIDEO_FPS},"
            f"vignette=PI/4[bg];"
            f"[1:v]scale=w='340+16*sin(2*PI*t/2.4)':h=-1:eval=frame[tamer];"
            f"[2:v]scale=w='340+16*sin(2*PI*t/2.4+PI)':h=-1:eval=frame[user];"
            f"[bg][tamer]overlay=x='(W/2+26)':y='(H*0.4-h/2)':eval=frame[bgtamer];"
            f"[bgtamer][user]overlay=x='(W/2-26-w)':y='(H*0.4-h/2)':eval=frame[vraw];"
        )
        filter_complex += self._build_sting_filters(
            '[vraw]', '[vout]', duration, sting_input_index=3, watermark_input_index=4,
        )

        cmd = [
            'ffmpeg',
            '-loop', '1', '-i', background_path,
            '-loop', '1', '-i', tamer_avatar_path,
            '-loop', '1', '-i', user_avatar_path,
            '-framerate', str(VIDEO_FPS), '-i', os.path.join(sting_frames_dir, 'frame_%05d.png'),
            '-loop', '1', '-i', watermark_path,
            '-i', audio_path,
            '-filter_complex', filter_complex,
            '-map', '[vout]', '-map', '5:a',
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'veryfast', '-crf', '22',
            '-c:a', 'aac', '-b:a', '192k',
            '-t', f'{duration:.2f}',
            '-movflags', '+faststart',
            '-y', output_path,
            '-progress', 'pipe:1', '-nostats',
        ]

        # A flat 600s used to be plenty for a simple bg+avatars encode,
        # but the sting overlay's extra filter passes (split/tpad/
        # drawbox/overlay on top of zoompan+vignette) made this real-
        # time factor highly host-dependent - on a single-vCPU box this
        # measured ~4-5x realtime, so a 3.5-minute duet alone can take
        # 15+ minutes. Scale with the video's own duration (generous
        # 8x margin) instead of a fixed number that a longer duet, or a
        # slower host, would blow straight through - a spurious kill
        # here just means a wasted retry, not a wrong result, but it
        # was guaranteed to happen for anything but the shortest duets.
        timeout = max(600, int(duration * 8))
        self._run_with_progress(cmd, duration, progress_callback, timeout=timeout)

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError('Duet video render produced an empty file.')

    @staticmethod
    def _run_with_progress(cmd, duration, progress_callback, timeout=600):
        """Runs ffmpeg, reporting real encode progress (not a guess) by
        reading its own `-progress pipe:1` output - each `out_time_ms=`
        line is how far into the (known) output duration it's encoded
        so far, so that's a genuine percentage rather than a spinner.
        """
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1,
        )
        timer = threading.Timer(timeout, process.kill)
        timer.start()
        try:
            last_percent = -1
            for line in process.stdout:
                if not progress_callback or not line.startswith('out_time_ms='):
                    continue
                try:
                    out_time_ms = int(line.strip().split('=', 1)[1])
                except (ValueError, IndexError):
                    continue
                percent = max(0, min(99, int((out_time_ms / 1_000_000) / duration * 100)))
                if percent != last_percent:
                    last_percent = percent
                    progress_callback(percent)

            stderr_output = process.stderr.read()
            process.wait()
        finally:
            timer.cancel()

        if process.returncode != 0:
            raise RuntimeError(f'Duet video render failed: {stderr_output[-2000:]}')
