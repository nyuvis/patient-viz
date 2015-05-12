/**
 * Created by krause on 2014-05-15.
 */

var headList = [];
var headPrefix = "pHeadList_"

function refreshInfo(pid, person) {
  headList.forEach(function(sel) {
    sel.remove();
  });
  headList = [];

  var sel = d3.select("#pHeadList");
  var hasId = false;
  var id = pid;
  var selId = null;

  function addItem(item) {
    var li = sel.insert("li", ":first-child");
    var div = li.append("div");
    div.append("strong").text(item["name"] + ': ');
    if(item["id"] === "id") {
      hasId = true;
      selId = div.append("select");
      id = item["value"];
    } else {
      var span = div.append("span").attr({
        "id": headPrefix + item["id"]
      }).text(item["value"]);
      if("label" in item) {
        span.classed("label", true);
        if(item["label"] !== "") {
          span.classed("label-" + item["label"], true);
        }
      } else if(!Number.isNaN(+item["value"])) {
        span.classed("badge", true);
      }
    }
    headList.push(li);
  }

  person["info"].sort(function(a, b) {
    return d3.descending(a["id"], b["id"]);
  });
  person["info"].forEach(function(item) {
    addItem(item);
  });

  if(!hasId) {
    addItem({
      "id": "id",
      "name": "File",
      "value": pid
    });
  }

  function setSelect() {
    var found = false;
    selId.selectAll("option").each(function(p, i) {
      if(p !== id) {
        return;
      }
      var tmpChg = selId.on("change");
      selId.on("change", null);
      selId.node().selectedIndex = i;
      selId.on("change", tmpChg);
      found = true;
    });
    return found;
  }

  if(!setSelect()) {
    selId.append("option").text(id).datum(id);
    setSelect();
  }
  d3.select("#pStart").text(jkjs.time.pretty(person["start"]));
  d3.select("#pEnd").text(jkjs.time.pretty(person["end"]));
  return selId;
}

function initViews(mainG, secG, suppl, blank, eventList, typeList, overview, setBox, onVC, busy, updateViewport) {
  var res = [];
  var pool = new TypePool(busy, overview, setBox, onVC, 8, 8);
  pool.setSelections(mainG, secG);
  setupModes(pool);
  res.push(pool);
  setupRectSelection(pool, blank);
  setupClickAction(pool, blank);
  var supplH = 100;
  var topMargin = supplH - 32;
  setupAxisLabels(pool, suppl, supplH, topMargin);
  res.push(setupEventView(pool, eventList));
  res.push(setupTypeView(pool, typeList));
  res.push(setupLinechart(pool, suppl, topMargin));
  res.push(setupHistogram(pool, suppl, topMargin));
  res.push(new Labels(pool, updateViewport, blank));
  busy.setState(jkjs.busy.state.norm);
  return res;
}

function setupModes(pool) {
  var xSel = d3.select("#xMode").append("select");
  pool.getXModes().forEach(function(name) {
    xSel.append("option").text(name);
  });
  xSel.node().selectedIndex = pool.xMode();
  xSel.on("change", function() {
    pool.xMode(xSel.node().selectedIndex);
  });
  var ySel = d3.select("#yMode").append("select");
  pool.getYModes().forEach(function(name) {
    ySel.append("option").text(name);
  });
  ySel.node().selectedIndex = pool.yMode();
  ySel.on("change", function() {
    pool.yMode(ySel.node().selectedIndex);
  });
}

function loadPerson(pid, person, pool, eventView, typeView, linechart, histogram, dictionary, suppl) {
  var selId = refreshInfo(("" + pid).trim(), person);
  pool.clearEvents();
  pool.readEvents(person, dictionary);
  linechart.values("total" in person ? person["total"] : []);
  if(!linechart.hasContent()) { // FIXME make possible for both to show at the same time
    var claims = {};
    var claimToTime = {};
    var noHistogram = true;
    pool.traverseAllEvents(function(_, _, e) {
      var claim = e.getEventGroupId();
      var cost = e.cost();
      if(cost) {
        noHistogram = false;
      }
      var t = e.getTime();
      if(!claim.length) {
        claim = "__time__" + t;
      }
      if(claim in claims) {
        if(claim.indexOf("__time__") === 0) {
          claims[claim] += cost;
        } else {
          claims[claim] === cost || console.warn("cost mismatch", claims[claim], cost);
          if(claimToTime[claim] > t) {
            claimToTime[claim] = t;
          }
        }
      } else {
        claims[claim] = cost;
        claimToTime[claim] = t;
      }
    });
    var times = {};
    Object.keys(claims).forEach(function(claim) {
      var cost = claims[claim];
      var t = claimToTime[claim];
      if(!(t in times)) {
        times[t] = cost;
      } else {
        times[t] += cost;
      }
    });
    if(!noHistogram) {
      histogram.values(Object.keys(times).map(function(t) {
        return [ t, times[t] ];
      }));
      jkjs.util.toFront(histogram.getG(), false);
    }
  }
  var sh = linechart.hasContent() || histogram.hasContent() ? 100 : 32;
  suppl.style({
    "height": sh + "px"
  });
  pool.hasLinechart(linechart.hasContent() || histogram.hasContent());
  typeView.updateLists();
  setupBars(pool, person);
  setupYCluster(pool, d3.select("#pYCluster"), typeView);
  pool.updateLook();
  return selId;
}

function setupBars(pool, person) {
  if("classes" in person) {
    Object.keys(person["classes"]).forEach(function(key) {
      pool.addStyleClass(key, person["classes"][key]);
    });
  }
  if("h_bars" in person) {
    person["h_bars"].forEach(function(obj) {
      pool.addHBar(obj["group"], obj["id"], true);
    });
  }
  var auto = false;
  if("v_bars" in person) {
    person["v_bars"].forEach(function(time) {
      if(time == "auto") {
        auto = true;
      } else {
        pool.addVBar(time, true);
      }
    });
  }
  if("v_spans" in person) {
    person["v_spans"].forEach(function(span) {
      var from = +span["from"];
      var to = "to" in span ? +span["to"] : Number.NaN;
      var styleClass = "class" in span ? span["class"] : "";
      pool.addVSpan(from, to, styleClass, true);
    });
  }
  if(auto) {
    // find areas of interest
    var windowSize = 3;
    var minSlope = 15;
    var coolSlope = 2;
    var times = [];
    var slopes = [];
    var lastPeak = 0;
    pool.traverseDays(function(time, events) {
      var slope = 0;
      events.forEach(function(e) {
        slope += e.isFirstOfType() ? 1 : 0;
      });
      slopes.push(slope);
      times.push(time);
      if(slopes.length > windowSize) {
        slopes.shift();
        times.shift();
      }
      var sum = jkjs.stat.sum(slopes);
      if(sum > minSlope && !lastPeak) {
        pool.addVBar(times[0], true);
        lastPeak = sum;
      } else if(sum < coolSlope) {
        lastPeak = 0;
      }
    });
    // set labels
    var ignoreType = {};
    pool.traverseVBars(function(from, to, bar) {
      if(!bar) return;
      var counts = {};
      var types = [];
      pool.traverseEventsForTimespan(from, to, function(e) {
        var type = e.getType();
        var id = type.getId();
        if(id in ignoreType) return;
        if(e.isFirstOfType()) {
          types.push(type);
        }
        if(id in counts) {
          counts[id] += e.cost() || 1;
        } else {
          counts[id] = e.cost() || 1;
        }
      });
      types.sort(function(a, b) {
        return d3.descending(counts[a.getId()], counts[b.getId()]);
      });
      var top = types.slice(0, Math.min(10, types.length));
      top.forEach(function(type) {
        bar.labels.push(type);
        ignoreType[type.getId()] = true;
      });
    });
  }
}

function setupRectSelection(pool, blank) {
  var sel = pool.select();
  var selectionRect = sel.append("rect").style({
    "opacity": 0,
    "fill": "cornflowerblue"
  });
  jkjs.util.toFront(selectionRect, false);
  var rect = null;

  function makeAbsRect(rect) {
    return {
      "x": rect.width < 0 ? rect.x + rect.width : rect.x,
      "y": rect.height < 0 ? rect.y + rect.height : rect.y,
      "width": Math.abs(rect.width),
      "height": Math.abs(rect.height)
    };
  }

  function updateSelectionRect() {
    if(!rect) {
      jkjs.util.attr(selectionRect, {
        "x": 0,
        "y": 0,
        "width": 0,
        "height": 0
      }).style({
        "opacity": 0
      });
      return;
    }
    jkjs.util.attr(selectionRect, makeAbsRect(rect)).style({
      "opacity": 0.5
    });
  }

  var drag = d3.behavior.drag().on("dragstart", function() {
    var eve = d3.event.sourceEvent;
    if(!eve.shiftKey) return;
    eve.stopPropagation();
    var cur = pool.getMousePos();
    rect = {
      x: cur[0],
      y: -0.5 * jkjs.util.BIG_NUMBER,
      width: 0,
      height: jkjs.util.BIG_NUMBER
    };
    updateSelectionRect();
  }).on("drag", function() {
    blank.__ignoreClick = true;
    if(!rect) return;
    var cur = pool.getMousePos();
    rect.width = cur[0] - rect.x;
    pool.selectInRect(makeAbsRect(rect), false);
    updateSelectionRect();
  }).on("dragend", function() {
    if(rect) {
      pool.selectInRect(makeAbsRect(rect), true);
      blank.__ignoreClick = true;
    }
    rect = null;
    updateSelectionRect();
  });
  blank.call(drag);
}

function setupClickAction(pool, blank) {
  var lastE = null;
  blank.on("click", function() {
    if(blank.__ignoreClick) {
      blank.__ignoreClick = false;
      return;
    }
    var cur = pool.getMousePos();
    var hasEvent = false;
    pool.startBulkSelection();
    if(!pool.joinSelections()) {
      pool.traverseEvents(function(gid, tid, e) {
        e.setSelected(false);
      });
    }
    var first = null;
    if(pool.verticalSelection()) {
      pool.traverseEventsForX(cur[0], function(e) {
        if(!first) first = e;
        e.setSelected(true);
      });
    } else {
      pool.traverseTypes(function(gid, tid, type) {
        var rangeY = pool.getRangeY(type);
        if(cur[1] >= rangeY[0] && cur[1] < rangeY[1]) {
          type.traverseEvents(function(e) {
            if(!first) first = e;
            e.setSelected(true);
          });
        }
      });
    }
    pool.highlightEvent(first);
    pool.endBulkSelection();
  });
  if(SHOW_EVENT_GROUPS) {
    blank.on("mousemove", function() {
      var cur = pool.getMousePos();
      var e = null;
      pool.traverseEventsForX(cur[0], function(eve) {
        if(e) return;
        var rangeY = pool.getRangeY(eve.getType());
        if(cur[1] >= rangeY[0] && cur[1] < rangeY[1]) {
          e = eve;
        }
      });
      if(lastE === e) return;
      lastE = e;
      pool.updateEventGroupLines(e);
    });
  }
  pool.updateSelection();
}

function setupAxisLabels(pool, suppl, h, topMargin) {
  suppl.style({
    "height": h + "px"
  });
  var translate = suppl.append("g").attr({
    "transform": "translate(0 " + topMargin + ")"
  })
  var xAxisLabel = translate.append("g").classed("xAxisClass", true);
  var tAxis = d3.svg.axis();
  var tc = d3.time.scale();
  // var notFull = false;
  pool.addSizeListener(function(w, _) {
    suppl.style({
      "width": w + "px"
    });
    if(!vis) return;
    tc.range([ 0, w ]);
    tAxis.scale(tc);
    xAxisLabel.call(tAxis);
  });
  var tm = topMargin;
  var vis = true;
  pool.addViewportChangeListener(function(svgport, viewport, scale, smooth) {
    if(!pool.hasLinechart()) {
      suppl.style({
        "margin-top": "-4px"
      });
    }
    var dy = pool.hasLinechart() ? topMargin : 0;
    if(dy !== tm) {
      translate.attr({
        "transform": "translate(0 " + dy + ")"
      });
      tm = dy;
    }
    var needVis = pool.showTicks() && pool.linearTime();
    if(needVis != vis) {
      vis = needVis;
      xAxisLabel.style({
        "opacity": vis ? null : 0
      });
      pool.setVGrids([]);
    }
    if(!vis) return;

    var left = pool.getDateByX(viewport.x);
    var right = pool.getDateByX(viewport.x + viewport.width);
    var tExtent = d3.extent([ left, right ]);
    tc.domain(tExtent);
    tAxis.scale(tc);
    jkjs.zui.asTransition(xAxisLabel, smooth).call(tAxis);
    var ticks = [];
    var scaling = tAxis.scale();
    xAxisLabel.selectAll(".tick").each(function(d) {
      ticks.push(scaling(d));
    });
    pool.setVGrids(ticks);
  });
}

function setupLinechart(pool, suppl, topMargin) {
  var lc = new Linechart(suppl);
  var timeMap = function(t) {
    var vis = pool.linearTime();
    return vis ? pool.getXByTime(t) : 0;
  };
  var yMap = function(v) {
    var vis = pool.linearTime();
    return vis ? (1 - v) * topMargin : topMargin;
  };
  lc.mapping([ timeMap, yMap ]);
  pool.addViewportChangeListener(function(svgport, viewport, scale, smooth) {
    var g = lc.getG();
    var gt = jkjs.zui.asTransition(g, smooth);
    var sx = scale;
    var dx = -viewport.x;
    gt.attr({
      "transform": "scale(" + sx + " 1) translate(" + dx + " 0)"
    });
  });
  pool.addSizeListener(function(w, _) {
    lc.updateWidth(w);
  });
  return lc;
}

function setupHistogram(pool, suppl, topMargin) {
  var hs = new Histogram(suppl);
  var timeMap = function(t) {
    var vis = pool.linearTime();
    return vis ? pool.getXByTime(t) : 0;
  };
  var yMap = function(v) {
    var vis = pool.linearTime();
    return vis ? (1 - v) * topMargin : topMargin;
  };
  hs.mapping([ timeMap, yMap ]);
  pool.addViewportChangeListener(function(svgport, viewport, scale, smooth) {
    var g = hs.getG();
    var gt = jkjs.zui.asTransition(g, smooth);
    var sx = scale;
    var dx = -viewport.x;
    gt.attr({
      "transform": "scale(" + sx + " 1) translate(" + dx + " 0)"
    });
  });
  pool.addSizeListener(function(w, _) {
    hs.updateWidth(w);
  });
  return hs;
}

function setupEventView(pool, eventList) {
  var eView = new EventView(eventList);
  eView.connectPool(pool);

  function groupId(e) {
    var type = e.getType();
    return {
      id: type.getGroupId(),
      desc: type.getGroup()
    };
  }

  function groupTime(e) {
    return {
      id: e.getTime(),
      desc: jkjs.time.pretty(e.getTime())
    };
  }

  function sortNum(a, b) {
    return d3.ascending(a.getDesc().toUpperCase(), b.getDesc().toUpperCase());
  }

  function sortName(a, b) {
    return d3.ascending(a.getType().getName().toUpperCase(), b.getType().getName().toUpperCase());
  }

  function sortCount(a, b) {
    var c = d3.descending(a.getType().getCount(), b.getType().getCount());
    if(c) return c;
    return sortName(a, b);
  }

  function sortFirst(a, b) {
    var f = d3.descending(a.getType().getY(), b.getType().getY());
    if(f) return f;
    return sortName(a, b);
  }

  eView.addSortAndGroup("Group & Number", sortNum, groupId);
  eView.addSortAndGroup("Group & Name", sortName, groupId);
  var sag = eView.addSortAndGroup("Group & Count", sortCount, groupId);
  eView.addSortAndGroup("Group & First", sortFirst, groupId);
  eView.addSortAndGroup("Time & Number", sortNum, groupTime);
  eView.addSortAndGroup("Time & Name", sortName, groupTime);
  eView.addSortAndGroup("Time & Count", sortCount, groupTime);
  eView.addSortAndGroup("Time & First", sortFirst, groupTime);
  eView.selectSortAndGroup(sag);
  return eView;
}

function setupTypeView(pool, typeList) {
  var tView = new TypeView(pool, typeList, d3.select("#hCon")); // TODO use proper position

  function sortNum(a, b) {
    return d3.ascending(a.getDesc().toUpperCase(), b.getDesc().toUpperCase());
  }

  function sortName(a, b) {
    return d3.ascending(a.getName().toUpperCase(), b.getName().toUpperCase());
  }

  function sortCount(a, b) {
    var c = d3.descending(a.getCount(), b.getCount());
    if(c) return c;
    return sortName(a, b);
  }

  function sortFirst(a, b) {
    var f = d3.descending(a.getY(), b.getY());
    if(f) return f;
    return sortName(a, b);
  }

  tView.addSort("Number", sortNum);
  tView.addSort("Name", sortName);
  var s = tView.addSort("Count", sortCount);
  tView.addSort("First", sortFirst);

  tView.selectSort(s); // updates list
  return tView;
}

var yCompressClustering = false;
function setupYCluster(pool, sel, typeView) {
  var busy = pool.getBusy();
  var levels = [];
  if(yCompressClustering) {
    levels = [ 0, 1 ];
  } else {
    typeView.getNodeRoots().forEach(function(root) {
      root.preorder(function(level, n) {
        while(level > levels.length) {
          levels.push(levels.length);
        }
      }, 0, false);
    });
  }
  var opts = sel.selectAll("option").data(levels, function(d) { return d; });
  opts.exit().remove();
  opts.enter().append("option").text(function(d) {
    return "" + (levels.length - d - 1);
  });

  function updateYCompress() {
    var lvl = sel.node().selectedIndex;
    if(yCompressClustering) {
      if(lvl == 0) {
        pool.startBulkValidity();
        pool.traverseTypes(function(gid, tid, type) {
          type.proxyType(type);
        });
        pool.endBulkValidity();
      } else {
        busy.setState(jkjs.busy.state.busy);
        setTimeout(function() {
          var error = true;
          try {
            new EventClusterer().distance(function(vecA, vecB) {
              // levenshtein, 3, 3 // 10, 5
              // hamming, 5, 3
              // jaccard, 0.5, 1
              return jkjs.stat.edit_distances.hamming(vecA, vecB);
            }).threshold(5).minCluster(3).compute(pool).assignProxies();
            error = false;
          } finally {
            busy.setState(error ? jkjs.busy.state.warn : jkjs.busy.state.norm, error ? "Error while clustering." : "");
          }
        }, 0);
      }
    } else {
      pool.startBulkValidity();
      var roots = typeView.getNodeRoots();
      roots.forEach(function(root, ix) {
        root.preorder(function(level, n, hasChildren) {
          if(lvl + 1 > level && hasChildren) {
            n.setExpanded(true);
          }
        }, 0, false);
        root.preorder(function(level, n, hasChildren) {
          if(lvl + 1 == level && hasChildren) {
            n.setExpanded(false);
          }
        }, 0, false);
      });
      pool.endBulkValidity();
      typeView.updateLists();
    }
  }

  sel.node().selectedIndex = Math.floor(levels.length / 2);
  sel.on("change", updateYCompress);
  updateYCompress();
}
