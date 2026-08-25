// Tab switching logic
document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
  tab.addEventListener('click', function(e) {
    e.preventDefault();
    const target = this.getAttribute('data-bs-target');
    
    // Remove active class from all tabs and contents
    document.querySelectorAll('.nav-link').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(c => {
      c.classList.remove('show', 'active');
    });
    
    // Add active class to clicked tab and target content
    this.classList.add('active');
    document.querySelector(target).classList.add('show', 'active');
  });
});
