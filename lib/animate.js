(function(global) {
  'use strict';

  if (!CanvasRenderingContext2D.prototype.roundRect) {
    CanvasRenderingContext2D.prototype.roundRect = function(x, y, w, h, radii) {
      var r = typeof radii === 'number' ? radii : (radii && radii[0]) || 0;
      r = Math.min(r, w / 2, h / 2);
      this.moveTo(x + r, y);
      this.arcTo(x + w, y, x + w, y + h, r);
      this.arcTo(x + w, y + h, x, y + h, r);
      this.arcTo(x, y + h, x, y, r);
      this.arcTo(x, y, x + w, y, r);
      return this;
    };
  }

  var ease = {
    linear: function(t) { return t; },
    easeIn: function(t) { return t * t; },
    easeOut: function(t) { return 1 - Math.pow(1 - t, 3); },
    easeInOut: function(t) {
      return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
    },
    bounce: function(t) {
      var n1 = 7.5625, d1 = 2.75;
      if (t < 1 / d1) return n1 * t * t;
      if (t < 2 / d1) return n1 * (t -= 1.5 / d1) * t + 0.75;
      if (t < 2.5 / d1) return n1 * (t -= 2.25 / d1) * t + 0.9375;
      return n1 * (t -= 2.625 / d1) * t + 0.984375;
    },
    elastic: function(t) {
      return Math.pow(2, -10 * t) * Math.sin((t - 0.075) * (2 * Math.PI) / 0.3) + 1;
    }
  };

  function animate(opts) {
    var from = opts.from, to = opts.to;
    var duration = opts.duration || 400;
    var easingFn = typeof opts.easing === 'function' ? opts.easing
      : ease[opts.easing] || ease.easeOut;
    var onUpdate = opts.onUpdate;
    var onComplete = opts.onComplete;
    var start = performance.now();
    var delta = to - from;
    function tick(now) {
      var t = Math.min((now - start) / duration, 1);
      var value = from + delta * easingFn(t);
      if (onUpdate) onUpdate(value, t);
      if (t < 1) requestAnimationFrame(tick);
      else if (onComplete) onComplete();
    }
    requestAnimationFrame(tick);
  }

  function fadeIn(el, duration, delay) {
    duration = duration || 400; delay = delay || 0;
    el.style.opacity = '0'; el.style.display = '';
    el.style.transition = 'opacity ' + duration + 'ms ease-out';
    if (delay) el.style.transitionDelay = delay + 'ms';
    requestAnimationFrame(function() {
      requestAnimationFrame(function() { el.style.opacity = '1'; });
    });
    return new Promise(function(resolve) { setTimeout(resolve, duration + delay); });
  }

  function slideIn(el, direction, duration, delay) {
    direction = direction || 'up'; duration = duration || 400; delay = delay || 0;
    var dirMap = {
      up: ['translateY(20px)', 'translateY(0)'],
      down: ['translateY(-20px)', 'translateY(0)'],
      left: ['translateX(20px)', 'translateX(0)'],
      right: ['translateX(-20px)', 'translateX(0)']
    };
    var transforms = dirMap[direction] || dirMap.up;
    el.style.transform = transforms[0]; el.style.opacity = '0';
    el.style.transition = 'transform ' + duration + 'ms cubic-bezier(0.22, 1, 0.36, 1), opacity ' + duration + 'ms ease-out';
    if (delay) el.style.transitionDelay = delay + 'ms';
    requestAnimationFrame(function() {
      requestAnimationFrame(function() {
        el.style.transform = transforms[1]; el.style.opacity = '1';
      });
    });
    return new Promise(function(resolve) { setTimeout(resolve, duration + delay); });
  }

  function countUp(el, target, duration, suffix) {
    duration = duration || 1000; suffix = suffix || '';
    el.textContent = '0' + suffix;
    animate({
      from: 0, to: target, duration: duration, easing: 'easeOut',
      onUpdate: function(value) { el.textContent = Math.floor(value) + suffix; },
      onComplete: function() { el.textContent = target + suffix; }
    });
  }

  function scaleIn(el, duration, delay) {
    duration = duration || 400; delay = delay || 0;
    el.style.transform = 'scale(0.9)'; el.style.opacity = '0';
    el.style.transition = 'transform ' + duration + 'ms cubic-bezier(0.34, 1.56, 0.64, 1), opacity ' + duration + 'ms ease-out';
    if (delay) el.style.transitionDelay = delay + 'ms';
    requestAnimationFrame(function() {
      requestAnimationFrame(function() {
        el.style.transform = 'scale(1)'; el.style.opacity = '1';
      });
    });
    return new Promise(function(resolve) { setTimeout(resolve, duration + delay); });
  }

  function stagger(els, animFn, baseDelay, interval) {
    baseDelay = baseDelay || 0; interval = interval || 80;
    [].forEach.call(els, function(el, i) {
      setTimeout(function() { animFn(el, 400, 0); }, baseDelay + i * interval);
    });
  }

  function typingDots(container) {
    container.innerHTML = '<div class="typing"><span></span><span></span><span></span></div>';
    var style = document.createElement('style');
    style.textContent = '.typing{display:flex;gap:4px;padding:12px 16px;align-items:center}' +
      '.typing span{width:8px;height:8px;background:#6c8cff;border-radius:50%;animation:typingBounce 1.2s ease-in-out infinite}' +
      '.typing span:nth-child(2){animation-delay:0.2s}' +
      '.typing span:nth-child(3){animation-delay:0.4s}' +
      '@keyframes typingBounce{0%,60%,100%{transform:translateY(0);opacity:0.3}30%{transform:translateY(-8px);opacity:1}}';
    document.head.appendChild(style);
  }

  var THEME = {
    chartColors: ['#6c8cff', '#b89abe', '#7bab7a', '#f59e6f', '#8bb4ff', '#a8c4a0'],
    chartBg: 'rgba(255, 255, 255, 0.03)',
    gridColor: 'rgba(255,255,255,0.04)',
    axisColor: 'rgba(255,255,255,0.08)',
    labelColor: 'rgba(255,255,255,0.25)',
    textColor: '#c8c8d0',
    darkBg: 'rgba(12, 12, 20, 0.9)'
  };

  function LineChart(canvas, data, opts) {
    opts = opts || {};
    var ctx = canvas.getContext('2d');
    var W = canvas.width, H = canvas.height;
    var dpr = window.devicePixelRatio || 1;
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
    ctx.scale(dpr, dpr);

    var pad = opts.padding || { top: 30, right: 20, bottom: 40, left: 60 };
    if (typeof pad === 'number') pad = { top: pad, right: pad, bottom: pad, left: pad };
    var colors = opts.colors || THEME.chartColors;
    var duration = opts.duration || 800;
    var labels = data.labels || [];
    var datasets = data.datasets || [];
    var chartW = W - pad.left - pad.right;
    var chartH = H - pad.top - pad.bottom;

    var allValues = [];
    datasets.forEach(function(ds) { allValues = allValues.concat(ds.data); });
    var minVal = Math.min.apply(null, allValues);
    var maxVal = Math.max.apply(null, allValues);
    var range = maxVal - minVal || 1;
    var paddingRatio = opts.paddingRatio || 0.12;
    minVal -= range * paddingRatio; maxVal += range * paddingRatio;
    range = maxVal - minVal;
    var xStep = chartW / Math.max(labels.length - 1, 1);

    function getX(i) { return pad.left + i * xStep; }
    function getY(v) { return pad.top + chartH - (v - minVal) / range * chartH; }

    function drawBg() {
      ctx.fillStyle = opts.backgroundColor || THEME.chartBg;
      ctx.beginPath(); ctx.roundRect(0, 0, W, H, 10); ctx.fill();
    }
    function drawGrid() {
      ctx.strokeStyle = THEME.gridColor; ctx.lineWidth = 1;
      for (var i = 0; i <= 4; i++) {
        var y = pad.top + (chartH / 4) * i;
        ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(W - pad.right, y); ctx.stroke();
      }
    }
    function drawAxes() {
      ctx.strokeStyle = THEME.axisColor; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(pad.left, pad.top); ctx.lineTo(pad.left, pad.top + chartH);
      ctx.lineTo(W - pad.right, pad.top + chartH); ctx.stroke();
      ctx.fillStyle = THEME.labelColor; ctx.font = '10px system-ui,sans-serif'; ctx.textAlign = 'center';
      var step = Math.max(1, Math.floor(labels.length / 10));
      for (var i = 0; i < labels.length; i += step) ctx.fillText(labels[i], getX(i), H - pad.bottom + 16);
      ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
      for (var j = 0; j <= 4; j++) {
        var val = minVal + (range / 4) * j;
        ctx.fillText(Math.round(val * 100) / 100, pad.left - 8, pad.top + chartH - (chartH / 4) * j);
      }
    }
    function drawLegend() {
      var lx = W - pad.right - 10, ly = pad.top + 8;
      ctx.textAlign = 'left'; ctx.textBaseline = 'top';
      for (var i = 0; i < datasets.length; i++) {
        ctx.fillStyle = colors[i % colors.length];
        ctx.beginPath(); ctx.arc(lx - 80, ly + i * 20 + 4, 4, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = THEME.textColor; ctx.font = '11px system-ui,sans-serif';
        ctx.fillText(datasets[i].label || '', lx - 70, ly + i * 20);
      }
    }
    function drawFill(di, progress) {
      var ds = datasets[di], pts = ds.data;
      var cnt = Math.floor(pts.length * progress);
      if (cnt < 2) return;
      var grad = ctx.createLinearGradient(0, pad.top, 0, pad.top + chartH);
      var c = colors[di % colors.length];
      grad.addColorStop(0, c + '25'); grad.addColorStop(1, c + '00');
      ctx.fillStyle = grad;
      ctx.beginPath(); ctx.moveTo(getX(0), pad.top + chartH);
      for (var i = 0; i < cnt; i++) ctx.lineTo(getX(i), getY(pts[i]));
      ctx.lineTo(getX(cnt - 1), pad.top + chartH); ctx.closePath(); ctx.fill();
    }
    function drawLines(progress) {
      datasets.forEach(function(ds, di) {
        var pts = ds.data, cnt = Math.max(0, Math.floor(pts.length * progress));
        drawFill(di, progress);
        if (cnt < 2) return;
        ctx.strokeStyle = colors[di % colors.length]; ctx.lineWidth = 2.5;
        ctx.lineJoin = 'round'; ctx.lineCap = 'round';
        ctx.beginPath();
        for (var i = 0; i < cnt; i++) {
          if (i === 0) ctx.moveTo(getX(i), getY(pts[i]));
          else ctx.lineTo(getX(i), getY(pts[i]));
        }
        ctx.stroke();
        var ptStep = Math.max(1, Math.floor(pts.length / 18));
        for (var j = 0; j < cnt; j += ptStep) {
          ctx.fillStyle = colors[di % colors.length];
          ctx.beginPath(); ctx.arc(getX(j), getY(pts[j]), 3.5, 0, Math.PI * 2); ctx.fill();
          ctx.strokeStyle = 'rgba(255,255,255,0.3)'; ctx.lineWidth = 1; ctx.stroke();
        }
      });
    }
    drawBg(); drawGrid(); drawAxes(); drawLegend();
    animate({
      from: 0, to: 1.02, duration: duration, easing: 'easeOut',
      onUpdate: function(p) { ctx.clearRect(pad.left, pad.top, chartW + 1, chartH + 1); drawGrid(); drawLines(p); },
      onComplete: function() { ctx.clearRect(pad.left, pad.top, chartW + 1, chartH + 1); drawGrid(); drawLines(1); }
    });
  }

  function BarChart(canvas, data, opts) {
    opts = opts || {};
    var ctx = canvas.getContext('2d');
    var W = canvas.width, H = canvas.height;
    var dpr = window.devicePixelRatio || 1;
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
    ctx.scale(dpr, dpr);
    var pad = opts.padding || { top: 25, right: 20, bottom: 40, left: 55 };
    if (typeof pad === 'number') pad = { top: pad, right: pad, bottom: pad, left: pad };
    var colors = opts.colors || THEME.chartColors;
    var duration = opts.duration || 600;
    var labels = data.labels || []; var values = data.values || [];
    var chartW = W - pad.left - pad.right; var chartH = H - pad.top - pad.bottom;
    var maxVal = Math.max.apply(null, values) || 1;
    var barW = chartW / labels.length * 0.6; var gap = chartW / labels.length * 0.4;
    function getX(i) { return pad.left + i * (barW + gap) + gap / 2; }
    function getH(v, p) { return (v / maxVal) * chartH * p; }
    ctx.fillStyle = THEME.chartBg; ctx.beginPath(); ctx.roundRect(0, 0, W, H, 10); ctx.fill();
    ctx.strokeStyle = THEME.gridColor; ctx.lineWidth = 1;
    for (var gl = 0; gl <= 4; gl++) {
      var gy = pad.top + (chartH / 4) * gl;
      ctx.beginPath(); ctx.moveTo(pad.left, gy); ctx.lineTo(W - pad.right, gy); ctx.stroke();
    }
    ctx.fillStyle = THEME.labelColor; ctx.font = '10px system-ui,sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'top';
    for (var li = 0; li < labels.length; li++) ctx.fillText(labels[li], getX(li) + barW / 2, H - pad.bottom + 10);
    ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
    for (var yj = 0; yj <= 4; yj++) {
      ctx.fillText(Math.round((maxVal / 4) * yj), pad.left - 8, pad.top + chartH - (chartH / 4) * yj);
    }
    animate({
      from: 0, to: 1, duration: duration, easing: 'easeOut',
      onUpdate: function(p) {
        ctx.clearRect(pad.left, pad.top, chartW + 1, chartH + 1);
        for (var bi = 0; bi < values.length; bi++) {
          var bx = getX(bi), bh = getH(values[bi], p), by = pad.top + chartH - bh;
          ctx.fillStyle = colors[bi % colors.length] + '70';
          ctx.beginPath(); ctx.roundRect(bx, by, barW, bh, [4, 4, 0, 0]); ctx.fill();
          ctx.fillStyle = colors[bi % colors.length];
          ctx.beginPath(); ctx.roundRect(bx + 1, by + 1, Math.max(0, barW - 2), Math.max(0, bh - 1), [3, 3, 0, 0]); ctx.fill();
        }
      }
    });
  }

  function setupNetwork(container, nodes, edges, opts) {
    opts = opts || {};
    if (typeof vis === 'undefined' || !vis.Network) {
      container.innerHTML = '<div style="color:#94a3b8;padding:20px;text-align:center">vis.js not loaded</div>';
      return null;
    }
    var data = { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) };
    var options = {
      nodes: {
        shape: 'dot', size: opts.nodeSize || 18,
        font: { size: 13, color: '#e2e8f0', face: 'system-ui' }, borderWidth: 0,
        color: {
          background: opts.nodeColor || '#6c8cff',
          border: opts.nodeBorder || '#4a6cd6',
          highlight: { background: '#b89abe', border: '#9a80a0' }
        },
        shadow: { enabled: true, size: 4 }
      },
      edges: {
        width: opts.edgeWidth || 2,
        color: { color: opts.edgeColor || 'rgba(255,255,255,0.12)', highlight: '#e07c5c' },
        smooth: { type: 'continuous' },
        font: { size: 10, color: 'rgba(255,255,255,0.4)', align: 'middle' },
        arrows: { to: { enabled: true, scaleFactor: 0.6 } }
      },
      physics: {
        enabled: true, solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          gravitationalConstant: opts.gravity || -60, centralGravity: 0.005,
          springLength: opts.springLength || 180, springConstant: 0.06, damping: 0.5
        },
        stabilization: { iterations: opts.stabilizationIterations || 150 }
      },
      interaction: { hover: true, tooltipDelay: 100, navigationButtons: true, keyboard: true }
    };
    try {
      return new vis.Network(container, data, options);
    } catch (e) {
      container.innerHTML = '<div style="color:#f87171;padding:20px;text-align:center">Error: ' + e.message + '</div>';
      return null;
    }
  }

  function onView(els, callback, opts) {
    opts = opts || {};
    var observer = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) { callback(entry.target); if (!opts.repeat) observer.unobserve(entry.target); }
      });
    }, { threshold: opts.threshold || 0.1, rootMargin: opts.rootMargin || '0px' });
    if (typeof els === 'string') els = document.querySelectorAll(els);
    if (!els.length) els = [els];
    [].forEach.call(els, function(el) { observer.observe(el); });
    return observer;
  }

  if (typeof global.anim8 === 'undefined') {
    global.anim8 = {
      animate: animate, ease: ease, THEME: THEME,
      fadeIn: fadeIn, slideIn: slideIn, scaleIn: scaleIn,
      countUp: countUp, stagger: stagger, typingDots: typingDots,
      LineChart: LineChart, BarChart: BarChart,
      setupNetwork: setupNetwork, onView: onView
    };
  }
})(typeof window !== 'undefined' ? window : this);
