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

  // === Global Toast Utility ===
  function showToast(message, type) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const typeClasses = {
      error:   'border-red-200 bg-red-50 text-red-800',
      warning: 'border-amber-200 bg-amber-50 text-amber-800',
      success: 'border-green-200 bg-green-50 text-green-800',
      info:    'border-blue-200 bg-blue-50 text-blue-800',
    };
    const cls = typeClasses[type] || typeClasses.info;
    const div = document.createElement('div');
    div.className = `toast rounded-lg border px-4 py-3 text-sm shadow-md ${cls}`;
    div.textContent = message;
    container.appendChild(div);
    setTimeout(() => div.remove(), 5000);
  }
  window.showToast = showToast;

  // === HTMX Global Error Handling ===
  document.body.addEventListener('htmx:sendError', function(e) {
    showToast('網路連線失敗，請確認網路狀態後再試', 'error');
  });
  document.body.addEventListener('htmx:responseError', function(e) {
    const status = e.detail.xhr?.status;
    if (status === 403) {
      showToast('操作被拒絕，請重新整理頁面', 'error');
    } else if (status === 500) {
      showToast('伺服器錯誤，請稍後再試', 'error');
    } else {
      showToast('請求失敗（' + (status || '未知') + '），請稍後再試', 'warning');
    }
  });

  // === View Transitions：底部導航平滑切換 ===
  if (!document.startViewTransition) return;

  let isTransitioning = false;

  document.addEventListener('click', function(e) {
    const anchor = e.target.closest('#bottom-nav a[href]');
    if (!anchor) return;

    const href = anchor.getAttribute('href');
    if (!href || href.startsWith('#') || href.startsWith('javascript')) return;

    const currentPath = window.location.pathname;
    const targetPath = new URL(href, window.location.origin).pathname;
    if (currentPath === targetPath) return;

    if (isTransitioning) {
      e.preventDefault();
      return;
    }

    e.preventDefault();
    isTransitioning = true;

    document.startViewTransition(() => {
      window.location.href = href;
    }).finished.catch(() => {
      isTransitioning = false;
      window.location.href = href;
    });
  });
})();
