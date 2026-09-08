// Shared helpers for building a shareable PNG "card" (Instagram Story
// ratio, 1080x1920) via Canvas 2D, and getting it into the user's hands
// - the native share sheet (with the image attached, not just a link)
// where supported, a plain download otherwise. Used by the daily-guess
// win screen and the personal recap page.
(function () {
  // Cover art can point at a third-party CDN (e.g. imported from
  // Anghami) that sends no Access-Control-Allow-Origin header - loading
  // it with crossOrigin='anonymous' then fails outright (the browser's
  // CORS-mode fetch is refused), and without crossOrigin set at all the
  // canvas would just be "tainted" and throw on toBlob()/toDataURL()
  // later instead. Routing anything not already same-origin through our
  // own same-origin proxy (see backend.website_app.proxy_views) sidesteps
  // both - the proxy fetches it server-side and hands it back from our
  // own domain, which needs no CORS header at all.
  function resolveImageSrc(src) {
    try {
      var isSameOrigin = new URL(src, window.location.href).origin === window.location.origin;
      if (!isSameOrigin) return '/img-proxy/?url=' + encodeURIComponent(src);
    } catch (e) { /* a relative/malformed URL - just use it as-is below */ }
    return src;
  }

  function loadImage(src) {
    return new Promise(function (resolve, reject) {
      if (!src) { reject(new Error('no src')); return; }
      var img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = function () { resolve(img); };
      img.onerror = reject;
      img.src = resolveImageSrc(src);
    });
  }

  function roundRectPath(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  // Draws `img` cropped (cover-fit, not stretched) into a rounded box.
  function drawCoverImage(ctx, img, x, y, w, h, radius) {
    ctx.save();
    roundRectPath(ctx, x, y, w, h, radius);
    ctx.clip();
    var scale = Math.max(w / img.width, h / img.height);
    var sw = w / scale, sh = h / scale;
    var sx = (img.width - sw) / 2, sy = (img.height - sh) / 2;
    ctx.drawImage(img, sx, sy, sw, sh, x, y, w, h);
    ctx.restore();
  }

  function drawCircleImage(ctx, img, cx, cy, r) {
    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.closePath();
    ctx.clip();
    var scale = Math.max((r * 2) / img.width, (r * 2) / img.height);
    var sw = (r * 2) / scale, sh = (r * 2) / scale;
    var sx = (img.width - sw) / 2, sy = (img.height - sh) / 2;
    ctx.drawImage(img, sx, sy, sw, sh, cx - r, cy - r, r * 2, r * 2);
    ctx.restore();
  }

  // Word-wraps `text` inside `maxWidth`, drawing at most `maxLines`
  // (the last one ellipsized if there's more) - Arabic shapes correctly
  // through fillText as long as ctx.direction is set to 'rtl' first.
  function drawWrappedText(ctx, text, cx, y, maxWidth, lineHeight, maxLines) {
    var words = text.split(' ');
    var lines = [];
    var current = '';
    for (var i = 0; i < words.length; i++) {
      var attempt = current ? current + ' ' + words[i] : words[i];
      if (ctx.measureText(attempt).width > maxWidth && current) {
        lines.push(current);
        current = words[i];
      } else {
        current = attempt;
      }
      if (lines.length === maxLines) break;
    }
    if (lines.length < maxLines && current) lines.push(current);
    if (lines.length === maxLines) {
      var last = lines[maxLines - 1];
      while (ctx.measureText(last + '…').width > maxWidth && last.length > 1) {
        last = last.slice(0, -1);
      }
      lines[maxLines - 1] = last + (words.join(' ') !== lines.join(' ') ? '…' : '');
    }
    lines.forEach(function (line, idx) {
      ctx.fillText(line, cx, y + idx * lineHeight);
    });
    return lines.length;
  }

  function scatterSparkles(ctx, w, h, count, seedColor) {
    ctx.save();
    ctx.fillStyle = seedColor || 'rgba(255,255,255,.5)';
    for (var i = 0; i < count; i++) {
      var x = (i * 137.5) % w;
      var y = ((i * 977) % h);
      var r = 2 + (i % 4);
      ctx.globalAlpha = 0.25 + (i % 5) * 0.1;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  function canvasToBlob(canvas) {
    return new Promise(function (resolve) {
      canvas.toBlob(function (blob) { resolve(blob); }, 'image/png');
    });
  }

  function downloadBlob(blob, filename) {
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
  }

  // Tries the native share sheet with the image attached first (what
  // people expect on mobile - straight into WhatsApp/Instagram/etc.),
  // falling back to a plain download when that's not available.
  function shareOrDownloadBlob(blob, filename, shareText) {
    var file;
    try { file = new File([blob], filename, { type: 'image/png' }); } catch (e) { file = null; }
    if (file && navigator.canShare && navigator.canShare({ files: [file] })) {
      return navigator.share({ files: [file], text: shareText || '' }).catch(function () {
        downloadBlob(blob, filename);
      });
    }
    downloadBlob(blob, filename);
    return Promise.resolve();
  }

  window.ThShareCard = {
    loadImage: loadImage,
    roundRectPath: roundRectPath,
    drawCoverImage: drawCoverImage,
    drawCircleImage: drawCircleImage,
    drawWrappedText: drawWrappedText,
    scatterSparkles: scatterSparkles,
    canvasToBlob: canvasToBlob,
    shareOrDownloadBlob: shareOrDownloadBlob,
  };
})();
