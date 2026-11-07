/* Read-only DOM measurements for HTML + 3D slides. Inject into a browser page, then call measureSlideUI(). */
(() => {
  function measureSlideUI(options = {}) {
    const config = {
      pageSelector: '.deck-page:not([hidden]):not(.is-leaving), .slide.active, section.present',
      stageSelector: '#stage, .deck-stage',
      textSelector: 'h1,h2,h3,p,dd,dt,li,.status-line,.step-detail',
      columnSelector: '.text-panel,.case-panel,.inspection-main,.content-col',
      sceneSelector: '.scene-window,.canvas-host',
      captionSelector: '.caption,.example-label',
      footerSelector: '.slide-footer,.signature',
      ignoreTextSelector: 'pre,code,[data-verbatim]',
      disallowedRegex: null,
      ...options
    };
    const page = document.querySelector(config.pageSelector);
    if (!page) return { error: 'No active slide page matched', config };
    const stage = document.querySelector(config.stageSelector) || page;
    const scale = stage.getBoundingClientRect().width / (stage.offsetWidth || 1);
    const rect = el => el?.getBoundingClientRect();
    const shown = el => !!el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden';
    const orphans = [], disallowedMatches = [];
    for (const el of page.querySelectorAll(config.textSelector)) {
      if (!shown(el) || el.closest(config.ignoreTextSelector)) continue;
      const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT), lines = new Map();
      while (walker.nextNode()) {
        const node = walker.currentNode;
        if (node.parentElement.closest(config.ignoreTextSelector)) continue;
        for (const word of node.nodeValue.matchAll(/\S+/g)) {
          const range = document.createRange();
          range.setStart(node, word.index);
          range.setEnd(node, word.index + word[0].length);
          for (const box of range.getClientRects()) {
            const row = Math.round(box.top);
            if (!lines.has(row)) lines.set(row, []);
            lines.get(row).push(word[0]);
          }
        }
      }
      const rows = [...lines.entries()].sort((a, b) => a[0] - b[0]).map(x => x[1]);
      if (rows.length > 1 && rows.at(-1).length === 1) {
        orphans.push({ tag: el.tagName, text: el.textContent.trim(), lastLine: rows.at(-1) });
      }
      if (config.disallowedRegex && config.disallowedRegex.test(el.textContent)) {
        disallowedMatches.push({ tag: el.tagName, text: el.textContent.trim() });
      }
    }
    const caption = page.querySelector(config.captionSelector);
    const footer = page.querySelector(config.footerSelector);
    const column = page.querySelector(config.columnSelector);
    const scene = page.querySelector(config.sceneSelector);
    const nowrapTokens = [...page.querySelectorAll('.nowrap,.time-range,.metric-unit')].filter(shown).map(el => {
      const range = document.createRange();
      range.selectNodeContents(el);
      return { text: el.textContent, fragments: range.getClientRects().length, whiteSpace: getComputedStyle(el).whiteSpace };
    });
    const canvas = scene?.querySelector('canvas') || page.querySelector('canvas');
    const display = rect(canvas);
    return {
      page: page.dataset.slideId || page.id || null,
      stageScale: scale,
      orphanLastLines: orphans,
      disallowedMatches,
      nowrapTokens,
      footerGapStagePx: caption && footer ? (rect(footer).top - rect(caption).bottom) / scale : null,
      columnGapStagePx: column && scene ? (rect(scene).left - rect(column).right) / scale : null,
      canvas: canvas ? {
        width: canvas.width,
        height: canvas.height,
        requestedPhysicalWidth: display.width * devicePixelRatio,
        requestedPhysicalHeight: display.height * devicePixelRatio,
        widthDensityRatio: canvas.width / (display.width * devicePixelRatio || 1)
      } : null,
      note: 'Read-only DOM and canvas metrics. Combine with visual inspection of rendered frames.'
    };
  }
  globalThis.measureSlideUI = measureSlideUI;
})();
