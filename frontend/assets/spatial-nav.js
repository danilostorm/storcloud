(() => {
  const selector = 'a[href],button:not([disabled]),[tabindex="0"],[data-focusable]';
  let lastButtons = [];
  let repeatAt = 0;

  function visible(el) {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
  }

  function candidates() {
    return [...document.querySelectorAll(selector)].filter(visible);
  }

  function center(el) {
    const r = el.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  }

  function move(direction) {
    const list = candidates();
    if (!list.length) return;
    let current = document.activeElement;
    if (!list.includes(current)) {
      list[0].focus({ preventScroll: true });
      list[0].scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
      return;
    }
    const from = center(current);
    const vectors = {
      left: [-1, 0], right: [1, 0], up: [0, -1], down: [0, 1],
    };
    const [dx, dy] = vectors[direction];
    let best = null;
    let bestScore = Infinity;
    for (const el of list) {
      if (el === current) continue;
      const p = center(el);
      const vx = p.x - from.x, vy = p.y - from.y;
      const forward = vx * dx + vy * dy;
      if (forward <= 4) continue;
      const lateral = Math.abs(vx * dy - vy * dx);
      const score = forward + lateral * 2.25;
      if (score < bestScore) { best = el; bestScore = score; }
    }
    if (best) {
      best.focus({ preventScroll: true });
      best.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
    }
  }

  addEventListener('keydown', event => {
    const map = { ArrowLeft: 'left', ArrowRight: 'right', ArrowUp: 'up', ArrowDown: 'down' };
    if (map[event.key] && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)) {
      event.preventDefault(); move(map[event.key]);
    }
  });

  function press(buttons, index) { return !!buttons[index]?.pressed; }
  function gamepadLoop(now) {
    const pad = navigator.getGamepads?.()[0];
    if (pad) {
      document.documentElement.classList.add('gamepad-connected');
      const buttons = pad.buttons || [];
      const dirs = [
        [14, 'left'], [15, 'right'], [12, 'up'], [13, 'down'],
      ];
      for (const [index, dir] of dirs) {
        const held = press(buttons, index);
        const was = !!lastButtons[index];
        if ((held && !was) || (held && now >= repeatAt)) {
          move(dir); repeatAt = now + (was ? 150 : 350); break;
        }
      }
      if (press(buttons, 0) && !lastButtons[0] && document.activeElement?.click) document.activeElement.click();
      if (press(buttons, 1) && !lastButtons[1]) history.back();
      lastButtons = buttons.map(b => b.pressed);
    }
    requestAnimationFrame(gamepadLoop);
  }
  requestAnimationFrame(gamepadLoop);
})();
