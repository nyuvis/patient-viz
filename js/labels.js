/**
 * Created by krause on 2014-02-05.
 */

function Labels(pool, updateViewport, blank) {
  var that = this;
  var useLens = false;
  var lensCB = d3.select("#pUseLens").on("change", function() {
    useLens = lensCB.node().checked;
    lens.style({
      "opacity": useLens ? 0.25 : 0
    });
    that.clearScreen();
    updateViewport();
  });

  var lens = null;
  var lensView = null;
  var isInit = false;
  this.isInit = function(_) {
    if(!arguments.length) return isInit;
    isInit = !!_;
  };
  var lensX = Number.NaN;
  var lensY = Number.NaN;
  var lensW = Number.NaN;
  var lensH = Number.NaN;
  this.setLensView = function(x, y, w, h) {
    lensView.attr({
      "cx": x + w * 0.5,
      "cy": y + h * 0.5,
      "rx": w * 0.5,
      "ry": h * 0.5
    });
    lensX = x;
    lensY = y;
    lensW = w;
    lensH = h;
  };
  this.getLensView = function() {
    return {
      x: lensX,
      y: lensY,
      width: lensW,
      height: lensH
    };
  };

  var LENS_MOVE_WAIT = SLOW_MODE ? 500 : 0;
  var timeoutID = Number.NaN;
  var lastPos = [Number.NaN, Number.NaN];

  var poolSel = pool.selectSec();
  blank.on("mousemove.labels", function() {
    if(!that.isInit()) return;
    var pos = getMousePos(poolSel);
    if(pos[0] == lastPos[0] && pos[1] == lastPos[1]) {
      return;
    } else if(!Number.isNaN(timeoutID)) {
      clearTimeout(timeoutID);
    }
    lastPos = pos;
    timeoutID = setTimeout(function() {
      that.setLensView(lastPos[0] - lensW * 0.5, lastPos[1] - lensH * 0.5, lensW, lensH);
      updateViewport();
    }, LENS_MOVE_WAIT);
  });

  lens = poolSel.append("g").style({
    "opacity": 0
  });
  lensView = lens.append("ellipse").attr({
    "fill": "none",
    "stroke": "black",
    "stroke-width": 1
  });

  function getMousePos(sel) {
    return d3.mouse(sel.node());
  };

  this.pool = function() {
    return pool;
  };

  var mode = function() {
    if(useLens) {
      return TypePool.labelsLens;
    }
    return TypePool.hasWeightedEvent ? Labels.labelsByWeight : Labels.labelsByBars;
  };
  this.mode = function(_) {
    if(!arguments.length) return mode;
    mode = _;
    updateViewport();
  };
  this.setShowLabels = function(show) {
    lens.style({
      "opacity": useLens && show ? 0.25 : 0
    });
    pool.traverseTypes(function(gid, tid, type) {
      type.showLabels(show);
    });
  };
  this.clearScreen = function() {
    pool.traverseTypes(function(gid, tid, type) {
      that.noShow(type);
    });
  };
  this.noShow = function(type) {
    var show = type.showLabels();
    type.showLabels(false);
    type.showLabels(show);
  };
  this.positionLabel = function(type, x, y, width, vpx, vpy, scale, right, event) {
    var box = pool.boxSize();
    var colW = box[0];
    var rowH = box[1];
    var st = type.selectText();

    var gap = 20;
    var rx = right ? x - gap : x + gap;
    var fontSize = 8;
    st.style({
      "opacity": 1,
      "font-size": fontSize
    });
    if(type.textWidthCache() !== width || type.textOrientCache() != right) {
      jkjs.text.display(st, type.getName(), {
          x: right ? rx - width : rx,
          y: y,
          width: width,
          height: fontSize * 2
      }, false, right ? jkjs.text.align.right : jkjs.text.align.left);
      type.textWidthCache(width);
      type.textOrientCache(right);
    }
    jkjs.util.attr(st, {
      "x": rx,
      "y": y
    });

    var tY = (type.getY() + rowH * 0.5 - vpy) * scale;
    var tX;
    if(event) {
      tX = (pool.getXByEventTime(event) + colW * 0.5 - vpx) * scale;
    } else {
      tX = right ? rx + gap : rx - gap;
    }
    var sc = type.selectConnect();
    jkjs.util.attr(sc, {
      "x1": right ? rx + 5 : rx - 5,
      "y1": y - fontSize * 0.5,
      "x2": right ? tX - 5 : tX + 5,
      "y2": tY
    }).style({
      "opacity": 1
    });
  };

  pool.addViewportChangeListener(function(svgport, viewport, scale, smooth) {
    var func = mode();
    func(that, svgport, viewport, scale, smooth);
  });
} // Labels
Labels.labelsByBars = function(labels, svgport, viewport, scale, smooth) {
  var pool = labels.pool();
  var box = pool.boxSize();
  var colW = box[0];
  var rowH = box[1];

  pool.traverseVBars(function(from, to, bar) {
    if(!bar) return;
    var refType = bar.labels[0];
    var y = 10;
    bar.labels.sort(function(a, b) {
      return d3.ascending(a.getY(), b.getY());
    });
    bar.labels.forEach(function(type) {
      if(!type.isValid()) return;
      if(!type.showLabels()) return;
      y = Math.max(y, -10 + (-viewport.y + type.getY()) * scale);
      var event = type.getFirstEventAfter(from);
      if(!event) return;
      var x = (pool.getXByEventTime(event) - colW - viewport.x) * scale;
      labels.positionLabel(type, x, y, Math.min(Math.max(x - svgport.x - 4, 0), 200), viewport.x, viewport.y, scale, true, event);
      y += 10;
    });
  });
};
Labels.labelsByWeight = function(labels, svgport, viewport, scale, smooth) {
  if(!TypePool.hasWeightedEvent) return;
  var pool = labels.pool();

  pool.traverseTypes(function(gid, tid, type) {
    if(!type.showLabels() || !type.isValid()) {
      labels.noShow(type);
      return;
    }
    putLabel(type);
  });

  function putLabel(type) {
    var weightedEvent = null;
    type.traverseEventRange(viewport.x, viewport.x + viewport.width + 200, function(e) {
      return pool.getXByEventTime(e);
    }, function(e) {
      if(weightedEvent && weightedEvent.getWeight() >= e.getWeight()) return;
      if(e.isWeighted() && (scale > 1 || pool.isInTopTenWeight(e.getWeight()))) {
        weightedEvent = e;
      }
    });
    if(!weightedEvent || !weightedEvent.shown()) {
      labels.noShow(type);
      return;
    }
    var h = pool.getRangeY(type)[1] - pool.getRangeY(type)[0];
    var ex = (pool.getXByEventTime(weightedEvent) - viewport.x) * scale - 2;
    var ey = (type.getY() - viewport.y) * scale;
    var w = Math.min(Math.max(ex - svgport.x - 4, 0), 200);
    if(ey + h < 0 || ey > svgport.y + svgport.height || ex - w > svgport.x + svgport.width) {
      labels.noShow(type);
      return;
    }
    labels.positionLabel(type, ex, ey, Math.min(Math.max(ex - svgport.x - 4, 0), 200), viewport.x, viewport.y, scale, true, weightedEvent);
  }
};
TypePool.labelsLens = function(labels, svgport, viewport, scale, smooth) {
  var pool = labels.pool();
  var box = pool.boxSize();
  var colW = box[0];
  var rowH = box[1];
  var nw = Math.min(150 * scale * 1.25, 150);
  var nh = Math.min(150 * scale * 1.25, 150);
  var pLens = labels.getLensView();
  if(!labels.isInit() || pLens.width != nw || pLens.height != nh) {
    var w = nw;
    var h = nh;
    var x = labels.isInit() ? pLens.x + (pLens.width - nw) * 0.5 : (viewport.width * scale - w) * 0.5;
    var y = labels.isInit() ? pLens.y + (pLens.height - nh) * 0.5 : (viewport.height * scale - h) * 0.5;
    labels.setLensView(x, y, w, h);
    labels.isInit(true);
  }
  var lv = labels.getLensView();
  var rx = lv.width * 0.5;
  var ry = lv.height * 0.5;
  var cx = lv.x + lv.width * 0.5;
  var cy = lv.y + lv.height * 0.5;

  function xLeft(y) {
    return cx - Math.cos(Math.asin(Math.min(Math.max((cy - y) / ry, -1), 1))) * rx;
  }

  function xRight(y) {
    return cx + Math.cos(Math.asin(Math.min(Math.max((cy - y) / ry, -1), 1))) * rx;
  }

  var types = [];
  var already = {};
  pool.traverseTypes(function(gid, tid, origType) {
    if(!origType.showLabels() || !origType.isValid()) {
      labels.noShow(origType);
      return;
    }
    var type = origType.proxyType();
    if(type !== origType) {
      labels.noShow(origType);
    }
    if(type.getTypeId() in already) {
      return;
    }
    already[type.getTypeId()] = true;
    // need origType to set all y positions since type doesn't necessarily have the correct values
    type.setY(origType.getY());
    var range = pool.getRangeY(type);
    var minY = -viewport.y + Math.min.apply(null, range);
    var maxY = -viewport.y + Math.max.apply(null, range);
    if(minY * scale < lv.y || maxY * scale > lv.y + lv.height) {
      labels.noShow(type);
      return;
    }
    var y = type.getY();
    var event = null;
    var lrPref = 0;
    var minD = Number.POSITIVE_INFINITY;
    var leftB = viewport.x + xLeft((-viewport.y + y + rowH * 0.5) * scale) / scale - colW * 0.5;
    var rightB = viewport.x + xRight((-viewport.y + y + rowH * 0.5) * scale) / scale; // + colW * 0.5;
    var mid = (leftB + rightB) * 0.5;
    type.traverseProxedEventRange(leftB, rightB, function(e) {
      return pool.getXByEventTime(e);
    }, function(e, x) {
      var dl = Math.abs(x - leftB);
      var dr = Math.abs(x - rightB);
      var dm = Math.abs(x - mid);
      if(dl < minD) {
        minD = dl;
        lrPref = -1;
        event = e;
      }
      if(dr < minD) {
        minD = dr;
        lrPref = 1;
        event = e;
      }
      if(dm * 2 < minD) {
        minD = dm * 2;
        lrPref = 0;
        event = e;
      }
    });
    if(event) {
      types.push([ type, event, lrPref ]);
    } else {
      labels.noShow(type);
    }
  });
  types.sort(function(a, b) {
    return d3.ascending(a[0].getY(), b[0].getY());
  });
  var y1 = lv.y;
  var y2 = lv.y;
  var rights = [];
  var lefts = [];
  types.forEach(function(row) {
    var type = row[0];
    var event = row[1];
    var lrPref = row[2];
    var y = type.getY();
    var right = lrPref == 0 ? Math.floor(y / rowH) % 2 : lrPref > 0 ? false : true;
    if(right) {
      y1 = Math.max(y1, -10 + (-viewport.y + y) * scale);
      rights.push([ type, xLeft((-viewport.y + y) * scale), y1, 200, scale, event ]);
      y1 += 10;
    } else {
      y2 = Math.max(y2, -10 + (-viewport.y + y) * scale);
      lefts.push([ type, xRight((-viewport.y + y) * scale), y2, 200, scale, event ]);
      y2 += 10;
    }
  });
  var yHeight1 = y1 - lv.y;
  var yShift1 = Math.min((lv.height - yHeight1) * 0.5, 0);
  rights.forEach(function(args) {
    labels.positionLabel(args[0], args[1], args[2] + yShift1, args[3], viewport.x, viewport.y, args[4], true, args[5]);
  });
  var yHeight2 = y2 - lv.y;
  var yShift2 = Math.min((lv.height - yHeight2) * 0.5, 0);
  lefts.forEach(function(args) {
    labels.positionLabel(args[0], args[1], args[2] + yShift2, args[3], viewport.x, viewport.y, args[4], false, args[5]);
  });
};
