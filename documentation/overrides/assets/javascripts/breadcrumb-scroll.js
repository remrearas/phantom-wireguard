// noinspection JSUnresolvedReference

/**
 * ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
 * ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
 * ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
 * ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
 * ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
 * ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
 * Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
 */

document.addEventListener('DOMContentLoaded', function() {
  const breadcrumbs = document.querySelectorAll('.phantom-breadcrumbs');

  breadcrumbs.forEach(function(breadcrumb) {
    const wrapper = breadcrumb.querySelector('.phantom-breadcrumbs-wrapper');
    if (!wrapper) return;

    // Check if content is scrollable
    function checkScroll() {
      if (wrapper.scrollWidth > wrapper.clientWidth) {
        breadcrumb.classList.add('has-scroll');

        // Scroll to the end to show current page
        wrapper.scrollLeft = wrapper.scrollWidth - wrapper.clientWidth;
      } else {
        breadcrumb.classList.remove('has-scroll');
      }
    }

    // Initial check
    checkScroll();

    // Check on window resize
    window.addEventListener('resize', checkScroll);

    // Optional: Add smooth scroll behavior for better UX
    wrapper.style.scrollBehavior = 'smooth';

    // Update gradient visibility on scroll
    wrapper.addEventListener('scroll', function() {
      const scrollLeft = wrapper.scrollLeft;
      const maxScroll = wrapper.scrollWidth - wrapper.clientWidth;

      // Show/hide left gradient
      if (scrollLeft > 0) {
        breadcrumb.classList.add('scrolled-right');
      } else {
        breadcrumb.classList.remove('scrolled-right');
      }

      // Show/hide right gradient
      if (scrollLeft < maxScroll - 1) {
        breadcrumb.classList.add('can-scroll-left');
      } else {
        breadcrumb.classList.remove('can-scroll-left');
      }
    });
  });
});