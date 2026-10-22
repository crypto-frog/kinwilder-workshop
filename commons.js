/* Four frames at most; resident content is already escaped, never interpreted. */
(() => {
  'use strict';
  const works = [...document.querySelectorAll('.exhibit')].map(el => ({el, frames: [...el.querySelectorAll('[data-frame]')], interval: Number(el.dataset.interval), frame: 0, visible: true}));
  if (!works.length) return;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const button = document.querySelector('#commons-motion');
  let paused = false, timer;
  try {paused = localStorage.getItem('outpost-exhibit-motion') === 'off';} catch {}
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) works.find(work => work.el === entry.target).visible = entry.isIntersecting;
  });
  works.forEach(work => observer.observe(work.el));
  function state() {
    clearInterval(timer); timer = undefined;
    button.textContent = reduced.matches ? '[ reduced motion ]' : paused ? '[ resume exhibits ]' : '[ pause exhibits ]';
    button.disabled = reduced.matches;
    button.setAttribute('aria-pressed', String(paused || reduced.matches));
    if (paused || reduced.matches || document.hidden) return;
    // A steady clock, not a timer per exhibit. Hidden work does no animation work.
    let elapsed = 0;
    works.forEach(work => {work.next = work.interval;});
    timer = setInterval(() => {
      elapsed += 250;
      for (const work of works) {
        if (elapsed < work.next) continue;
        work.next = elapsed + work.interval;
        if (!work.visible || work.frames.length < 2) continue;
        work.frames[work.frame].hidden = true;
        work.frame = (work.frame + 1) % work.frames.length;
        work.frames[work.frame].hidden = false;
      }
    }, 250);
  }
  button.hidden = false;
  button.addEventListener('click', () => {paused = !paused; try {localStorage.setItem('outpost-exhibit-motion', paused ? 'off' : 'on');} catch {} state();});
  reduced.addEventListener('change', state);
  document.addEventListener('visibilitychange', state);
  state();
})();
