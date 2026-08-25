// Tab state persistence using URL query parameters
document.addEventListener('DOMContentLoaded', function() {
  // Get the tab from URL query parameter
  const urlParams = new URLSearchParams(window.location.search);
  const savedTab = urlParams.get('tab');
  
  if (savedTab) {
    // Find the tab button and tab content
    const tabButton = document.querySelector(`[data-bs-target="#${savedTab}"]`);
    const tabContent = document.getElementById(savedTab);
    
    if (tabButton && tabContent) {
      // Remove active class from all tabs
      document.querySelectorAll('.nav-link').forEach(tab => {
        tab.classList.remove('active');
        tab.setAttribute('aria-selected', 'false');
        tab.setAttribute('tabindex', '-1');
      });
      
      document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('show', 'active');
      });
      
      // Add active class to saved tab
      tabButton.classList.add('active');
      tabButton.setAttribute('aria-selected', 'true');
      tabButton.removeAttribute('tabindex');
      
      tabContent.classList.add('show', 'active');
    }
  }
  
  // Save tab to URL when clicked
  document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tabButton => {
    tabButton.addEventListener('click', function() {
      const target = this.getAttribute('data-bs-target');
      const tabId = target.replace('#', '');
      
      // Update URL without page reload
      const url = new URL(window.location);
      url.searchParams.set('tab', tabId);
      window.history.replaceState({}, '', url);
    });
  });
});
