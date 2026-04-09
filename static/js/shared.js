/**
 * Shared JS for Exbooks
 */

(function() {
  // === Global Loading Indicator ===
  const globalLoader = document.getElementById('global-loader');
  const globalLoaderBar = document.getElementById('global-loader-bar');
  let loadingProgress = 0;
  let loadingInterval = null;

  function startLoading() {
    if (!globalLoader) return;
    globalLoader.style.opacity = '1';
    loadingProgress = 0;
    globalLoaderBar.style.width = '0%';
    
    loadingInterval = setInterval(() => {
      loadingProgress += Math.random() * 15;
      if (loadingProgress > 90) loadingProgress = 90;
      globalLoaderBar.style.width = loadingProgress + '%';
    }, 100);
  }

  function stopLoading() {
    if (!globalLoader) return;
    clearInterval(loadingInterval);
    globalLoaderBar.style.width = '100%';
    setTimeout(() => {
      globalLoader.style.opacity = '0';
      setTimeout(() => {
        globalLoaderBar.style.width = '0%';
      }, 200);
    }, 150);
  }

  // HTMX Event Listeners
  document.body.addEventListener('htmx:beforeRequest', startLoading);
  document.body.addEventListener('htmx:afterRequest', stopLoading);
  document.body.addEventListener('htmx:beforeSwap', stopLoading);

  // === Virtual Keyboard Handling ===
  if (window.visualViewport) {
    let originalHeight = document.body.style.height;
    
    window.visualViewport.addEventListener('resize', () => {
      document.body.style.height = `${window.visualViewport.height}px`;
      
      const activeElement = document.activeElement;
      if (activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA')) {
        setTimeout(() => {
          activeElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 100);
      }
    });

    window.visualViewport.addEventListener('scroll', () => {
      if (window.visualViewport.height === window.innerHeight) {
        document.body.style.height = originalHeight || '';
      }
    });
  }

  window.addEventListener('resize', () => {
    if (!window.visualViewport) {
      const activeElement = document.activeElement;
      if (activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA')) {
        setTimeout(() => {
          activeElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 100);
      }
    }
  });
})();
