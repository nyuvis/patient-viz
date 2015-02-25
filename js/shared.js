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

function loadPerson(pid, person, pool, eventView, typeView, linechart, dictionary, suppl) {
  var selId = refreshInfo(("" + pid).trim(), person);
  pool.clearEvents();
  pool.readEvents(person, dictionary);
  linechart.values("total" in person ? person["total"] : []);
  var sh = linechart.hasContent() ? 100 : 32;
  suppl.style({
    "height": sh + "px"
  });
  pool.hasLinechart(linechart.hasContent());
  typeView.updateLists();
  setupBars(pool, person);
  setupYCluster(pool, d3.select("#pYCluster"));
  pool.updateLook();
  return selId;
}

function setupBars(pool, person) {
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
          counts[id] += 1;
        } else {
          counts[id] = 1;
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
      y: cur[1],
      width: 0,
      height: 0
    };
    updateSelectionRect();
  }).on("drag", function() {
    blank.__ignoreClick = true;
    if(!rect) return;
    var cur = pool.getMousePos();
    rect.width = cur[0] - rect.x;
    rect.height = cur[1] - rect.y;
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
    var slot = [];
    pool.traverseEventsForX(cur[0], function(e) {
      var rangeY = pool.getRangeY(e.getType());
      if(cur[1] >= rangeY[0] && cur[1] < rangeY[1]) {
        e.setSelected(pool.joinSelections() ? true : !e.isSelected());
        hasEvent = true;
      }
      slot.push(e);
    });
    if(!hasEvent) {
      slot.forEach(function(e) {
        e.setSelected(true);
      });
    }
    pool.endBulkSelection();
  });
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
function setupYCluster(pool, sel) {
  var busy = pool.getBusy();
  sel.on("change", null);
  sel.node().checked = false;
  sel.on("change", function() {
    if(!sel.node().checked) {
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
          if(!yCompressClustering) {
            pool.startBulkValidity();
            pool.traverseTypes(function(gid, tid, type) {
              type.proxyType(type.getParent() || type);
            });
            pool.endBulkValidity();
          } else {
            computeRowClusters(pool, function(vecA, vecB) {
              // levenshtein, 3, 3 // 10, 5
              // hamming, 5, 3
              // jaccard, 0.5, 1
              return jkjs.stat.edit_distances.hamming(vecA, vecB);
            }, 5, 3);
          }
          error = false;
        } finally {
          busy.setState(error ? jkjs.busy.state.warn : jkjs.busy.state.norm);
        }
      }, 0);
    }
  });
}

function computeRowClusters(pool, distance, threshold, minCluster) {
  // init types
  console.log("init");
  var types = [];
  pool.traverseTypes(function(gid, tid, type) {
    if(type.hasEvents()) {
      types.push({
        type: type,
        vec: pool.toBitVector(type),
        neighbors: [],
        cluster: type,
        visited: false
      });
    }
  });
  // compute distances
  console.log("distances");
  var total = (types.length * types.length - types.length) * 0.5;
  var count = 0;
  var lastTime = new Date().getTime();
  for(var ix = 0;ix < types.length;ix += 1) {
    var objA = types[ix];
    var vecA = objA.vec;
    var curTime = new Date().getTime();
    if(curTime - lastTime > 1000) {
      console.log((count / total) * 100 + "%");
      lastTime = curTime;
    }
    for(var k = ix + 1;k < types.length;k += 1) {
      var objB = types[k];
      var vecB = objB.vec;
      var dist = distance(vecA, vecB);
      if(dist < threshold) {
        objA.neighbors.push(objB);
        objB.neighbors.push(objA);
      }
      count += 1;
    }
  }
  // dbscan
  console.log("dbscan");
  function expandCluster(obj, cluster) {
    obj.cluster = cluster;
    var list = [ obj.neighbors ];
    while(list.length) {
      list.shift().forEach(function(p) {
        if(!p.visited) {
          p.visited = true;
          if(p.neighbors.length >= minCluster) {
            list.push(p.neighbors);
          }
        }
        if(p.cluster === p.type) { // not in any other cluster yet
          p.cluster = cluster;
        }
      });
    }
  }

  function scan() {
    types.forEach(function(obj) {
      if(obj.visited) {
        return;
      }
      obj.visited = true;
      if(obj.neighbors.length >= minCluster) {
        expandCluster(obj, obj.cluster);
      }
    });
  }

  scan();
  // assign proxies
  console.log("assign proxies");
  pool.startBulkValidity();
  types.forEach(function(obj) {
    obj.type.proxyType(obj.cluster);
  });
  pool.endBulkValidity();
}
