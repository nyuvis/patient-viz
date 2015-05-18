/**
 * Created by krause on 2014-09-24.
 */

function Type(p, g, typeId, dictionary) {
  var that = this;
  var pool = p;
  var group = g;
  var gid = g.trim().replace(/[.#*]/gi, "_");
  var id = typeId;
  var desc = Type.typeDesc(g, typeId, false, dictionary, true);
  var type = typeId;
  var name = Type.typeDesc(g, typeId, false, dictionary, false);
  var events = [];
  var typeSpec = g in dictionary && typeId in dictionary[g] ? dictionary[group][id] : null;
  var color = (typeSpec && typeSpec["color"]) || null;
  var flags = (typeSpec && typeSpec["flags"]) || null;
  var allFlags = null;
  var parent = (typeSpec && typeSpec["parent"]) || "";
  if(parent == id && id !== "") {
    console.warn("parent to self", parent, id);
    parent = "";
  }
  var proxy = that;
  var proxed = {};
  proxed[id] = that;
  var proxedEvents = null;
  var proxedMinTime = Number.NaN;
  var proxedMaxTime = Number.NaN;

  this.changeProxed = function(type, add) {
    var id = type.getTypeId();
    if(add) {
      proxed[id] = type;
    } else {
      proxed[id] = null;
      delete proxed[id];
    }
    proxedEvents = null;
  };
  this.getProxed = function() {
    return Object.keys(proxed).map(function(id) {
      return proxed[id];
    });
  };

  function ensureProxedEvents() {
    if(proxedEvents) return;
    var events = [];
    that.getProxed().forEach(function(type) {
      type.traverseEvents(function(e) {
        events.push(e);
      });
    });
    events.sort(function(a, b) {
      return d3.ascending(a.getTime(), b.getTime());
    });
    if(events.length) {
      proxedMinTime = events[0].getTime();
      proxedMaxTime = events[events.length - 1].getTime();
    } else {
      proxedMinTime = Number.NaN;
      proxedMaxTime = Number.NaN;
    }
    proxedEvents = events;
  }

  this.getFirstProxedEvent = function() {
    ensureProxedEvents();
    return proxedEvents.length ? proxedEvents[0] : null;
  };
  this.traverseProxedEvents = function(cb) {
    ensureProxedEvents();
    proxedEvents.forEach(cb);
  };
  this.traverseProxedEventRange = function(fromX, toX, getX, cb) {
    // events are sorted by time -> x position
    ensureProxedEvents();
    proxedEvents.every(function(e) {
      var x = getX(e);
      if(x < fromX) return true;
      if(x >= toX) return false;
      e.shown() && cb(e, x);
      return true;
    });
  };
  this.proxedMinTime = function() {
    ensureProxedEvents();
    isNaN(proxedMinTime) && console.warn("NaN proxedMinTime", that);
    return proxedMinTime;
  };
  this.proxedMaxTime = function() {
    ensureProxedEvents();
    isNaN(proxedMaxTime) && console.warn("NaN proxedMaxTime", that);
    return proxedMaxTime;
  };
  this.proxyType = function(_) {
    if(!arguments.length) return proxy;
    // TODO temporarily lifted group ban
    // if(_.getGroup() !== that.getGroup()) {
    //   console.warn("proxy must have same group", _.getGroup(), that.getGroup());
    //   return;
    // }
    proxy.changeProxed(that, false);
    proxy = _;
    proxy.changeProxed(that, true);
    pool.onValidityChange();
  };
  this.hasRealProxy = function() {
    return that.proxyType() !== that;
  };

  this.getParentString = function() {
    return parent;
  };
  this.getParent = function() {
    if(id == "") return null;
    return pool.getTypeFor(g, parent);
  };
  this.getRoot = function() {
    if(!that.getParent()) return that;
    return that.getParent().getRoot();
  };

  this.getFlags = function() {
    if(allFlags) return allFlags;
    allFlags = flags || {};
    var p = this.getParent();
    if(p) {
      var f = p.getFlags();
      Object.keys(f).forEach(function(k) {
        if(!(k in allFlags)) {
          allFlags[k] = f[k];
        }
      });
    }
    return allFlags;
  };
  this.getColor = function(flag) {
    if(arguments.length) {
      var fs = that.getFlags();
      var f = flag.trim();
      if(f in fs) {
        return fs[f]["color"];
      }
    }
    if(color) return color;
    var p = this.getParent();
    if(p) {
      return p.getColor(); // all flags already checked
    }
    return "black"; // last resort
  };

  function validate(e) {
    if((type !== e["id"]) || (group !== e["group"])) {
      console.warn("mismatching type: " + id, group, type, e);
    }
  };

  this.getPool = function() {
    return pool;
  };
  this.addEvent = function(eve, e) {
    validate(e);
    events.push(eve);
  };
  var minTime = Number.NaN;
  var maxTime = Number.NaN;
  this.sortEvents = function() {
    events.sort(function(a, b) {
      return d3.ascending(a.getTime(), b.getTime());
    });
    var newEvents = [];
    var prevE = null;
    events.forEach(function(e) {
      if(prevE && prevE.getTime() === e.getTime()) {
        if(!prevE.eq(e)) {
          console.warn("removed non-equal duplicate: ", e.getDesc(), prevE.getDesc());
        }
        return;
      }
      newEvents.push(e);
      prevE = e;
    });
    events = newEvents;
    if(events.length) {
      minTime = events[0].getTime();
      maxTime = events[events.length - 1].getTime();
    } else {
      minTime = Number.NaN;
      maxTime = Number.NaN;
    }
    var minTimeDiff = Number.POSITIVE_INFINITY;
    var prevTime = minTime;
    events.forEach(function(e) {
      var time = e.getTime();
      var diff = time - prevTime;
      prevTime = time;
      if(!isNaN(diff) && diff > 0 && diff < minTimeDiff) {
        minTimeDiff = diff;
      }
    });
    return minTimeDiff;
  };
  this.hasEvents = function() {
    return events.length > 0;
  };
  this.getMinTime = function() {
    isNaN(minTime) && console.warn("NaN minTime", that);
    return minTime;
  };
  this.getMaxTime = function() {
    isNaN(maxTime) && console.warn("NaN maxTime", that);
    return maxTime;
  };
  this.getGroupId = function() {
    return gid;
  };
  this.getGroup = function() {
    return group;
  };
  this.getTypeId = function() {
    return id;
  };
  this.getId = function() {
    return type;
  };
  this.getCount = function() {
    return events.filter(function(e) {
      return e.shown();
    }).length;
  };
  this.getEventByIndex = function(ix) {
    var rix = 0;
    var elem = null;
    events.every(function(e) {
      if(rix > ix) return false;
      if(e.shown()) {
        if(rix == ix) {
          elem = e;
          return false;
        }
        rix += 1;
      }
      return true;
    });
    if(!elem) {
      console.warn("index out of bounds", ix);
    }
    return elem;
  };
  this.getFirstEventAfter = function(time) {
    var elem = null;
    events.every(function(e) {
      if(elem) return false;
      if(e.shown()) {
        if(e.getTime() >= time) {
          elem = e;
          return false;
        }
      }
      return true;
    });
    return elem;
  };
  this.getDesc = function() {
    return desc;
  };
  this.getName = function() {
    return name;
  };

  this.traverseEvents = function(cb) {
    events.forEach(function(e) {
      e.shown() && cb(e);
    });
  };
  this.traverseAllEvents = function(cb) { // even invisible ones
    events.forEach(function(e) {
      cb(e);
    });
  };
  this.traverseEventRange = function(fromX, toX, getX, cb) {
    // events are sorted by time -> x position
    events.every(function(e) {
      var x = getX(e);
      if(x < fromX) return true;
      if(x >= toX) return false;
      e.shown() && cb(e, x);
      return true;
    });
  };
  var showLabels = true;
  this.showLabels = function(_) {
    if(!arguments.length) return showLabels;
    showLabels = _;
    if(destroyed) return;
    if(!showLabels) {
      that.clearText();
      that.selectConnect().style({
        "opacity": 0
      });
    }
  };

  var y = 0;
  this.setY = function(yPos) {
    var oldY = y;
    y = yPos;
    if(oldY !== y && events.length > 0) {
      that.select().attr({
        "transform": "translate(0 "+y+")",
        "opacity": y < 0 ? 0 : null
      });
    }
  };
  this.getY = function() {
    return y;
  };

  var hBar = null;
  this.hBar = function(_) {
    if(!arguments.length) return hBar;
    hBar = _;
  };

  var sel = null;
  var destroyed = false;
  this.select = function() {
    if(destroyed) {
      console.warn("type already destroyed");
      return null;
    }
    if(!sel) {
      var pSel = that.getPool().select();
      sel = pSel.append("g").datum(that);
    }
    return sel;
  };
  var selConnect = null;
  this.selectConnect = function() {
    if(destroyed) {
      console.warn("type already destroyed");
      return null;
    }
    if(!selConnect) {
      var sSel = that.getPool().selectSec();
      selConnect = sSel.append("line").datum(that).style({
        "stroke": "black",
        "stroke-width": 1
      });
    }
    return selConnect;
  }
  var selText = null;
  this.selectText = function() {
    if(destroyed) {
      // console.warn("type already destroyed"); // TODO bug!!! #21
      return null;
    }
    if(!selText) {
      var sSel = that.getPool().selectSec();
      selText = sSel.append("text").datum(that).style({
        "fill": "black"
      });
      textWidthCache = Number.NaN;
    }
    return selText;
  };
  this.clearText = function() {
    if(!selText) return;
    selText.remove();
    selText = null;
    textWidthCache = Number.NaN;
  };
  var textWidthCache = Number.NaN;
  this.textWidthCache = function(_) {
    if(!arguments.length) return textWidthCache;
    textWidthCache = _;
  };
  var textOrientCache = false;
  this.textOrientCache = function(_) {
    if(!arguments.length) return textOrientCache;
    textOrientCache = _;
  };
  this.deleteType = function() {
    if(sel) {
      sel.remove();
      sel = null;
    }
    if(selText) {
      selText.remove();
      selText = null;
    }
    if(selConnect) {
      selConnect.remove();
      selConnect = null;
    }
    that.traverseEvents(function(e) {
      e.deleteEvent();
    });
    events = [];
    destroyed = true;
  };

  var valid = true;
  this.setValid = function(v) {
    var oldValid = valid;
    valid = !!v;
    if(valid != oldValid) {
      that.getPool().onValidityChange();
      if(!valid) {
        that.clearText();
        that.selectConnect().style({
          "opacity": 0
        });
      }
    }
  };
  this.isValid = function() {
    return valid;
  };

  var check = null;
  var span = null;
  var space = null;
  this.createListEntry = function(sel, level, isInner, isExpanded) {
    check = sel.append("input").attr({
      "type": "checkbox"
    }).on("change", function() {
      that.setValid(check.node().checked);
    });
    space = sel.append("span").style({
      "font-family": "monospace"
    }).text(" " + Array(level).join("|") + (!isInner ? "" : isExpanded ? "-" : "+"));
    span = sel.append("span").style({
      "margin-left": 4 + "px"
    }).text(that.getName()).on("click", function() {
      pool.startBulkSelection();
      if(!pool.joinSelections()) {
        pool.traverseEvents(function(gid, tid, e) {
          e.setSelected(false);
        });
      }
      var none = true;
      that.traverseProxedEvents(function(e) {
        e.setSelected(true);
        none = false;
      });
      if(none) {
        // we clicked on an inner node
        // we can determine selection through parenthood
        pool.traverseEvents(function(gid, tid, e) {
          var type = e.getType().proxyType();
          while(type) {
            if(type === that) {
              e.setSelected(true);
              break;
            }
            type = type.getParent();
          }
        });
      }
      pool.endBulkSelection();
    });
    return {
      "check": check,
      "span": span,
      "space": space
    };
  };
  this.updateListEntry = function(sel, hasSelected, onlyOneTypeSelected) {
    var color = that.getColor();
    span.style({
      "background-color": hasSelected ? color : null,
      "color": hasSelected ? jkjs.util.getFontColor(color) : null
    });
    if(hasSelected && onlyOneTypeSelected) {
      sel.node().scrollIntoView(true);
    }
    var tmp = check.on("change"); // disable notification when updating
    check.on("change", null);
    check.node().checked = that.isValid();
    check.on("change", tmp);
  };
} // Type
Type.typeDesc = function(group, id, asId, dictionary, full) {
  if(asId) {
    return (group+"__"+id).replace(/[.#*]/gi, "_");
  } else if(group in dictionary && id in dictionary[group]) {
    var desc = dictionary[group][id][full ? "desc" : "name"];
    if(group != "diagnosis" && group != "procedure") return desc;
    var rid = id.indexOf("__") >= 0 ? id.split("__", 2)[1] : id;
    if(rid.startsWith("HIERARCHY") || rid == '') return desc;
    if(desc == rid) {
      desc = "";
    }
    if(rid.indexOf('.') >= 0) return rid + (desc != "" ? ": " + desc : "");
    var letterstart = Number.isNaN(+rid.substring(0, 1));
    var pre = rid.substring(0, letterstart ? 4 : 3);
    var post = rid.substring(letterstart ? 4 : 3);
    return pre + "." + post + (desc != "" ? ": " + desc : "");
  } else {
    return (full ? group + " " : "") + rid
  }
};
