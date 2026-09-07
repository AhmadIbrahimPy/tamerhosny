// Web Push service worker - only handles push delivery + notification
// clicks. Deliberately does NOT do any fetch caching/offline support;
// this site isn't an offline-first app, and a caching SW here would
// risk serving stale HTML after a deploy.

self.addEventListener('push', function (event) {
  var payload = { title: 'أرشيف تامر حسني', body: '', url: '/' };
  if (event.data) {
    try { payload = Object.assign(payload, event.data.json()); } catch (e) {}
  }

  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.body,
      icon: payload.icon || '/static/images/logos/icon.jpeg',
      badge: payload.icon || '/static/images/logos/icon.jpeg',
      data: { url: payload.url || '/' },
    })
  );
});

self.addEventListener('notificationclick', function (event) {
  event.notification.close();
  var url = (event.notification.data && event.notification.data.url) || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (windowClients) {
      for (var i = 0; i < windowClients.length; i++) {
        var client = windowClients[i];
        if (client.url === url && 'focus' in client) return client.focus();
      }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});
