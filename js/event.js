/**
 * Created by krause on 2014-09-24.
 */

function Event(e, pool, dictionary) {
  var that = this;
  var id = Event.nextId();
  var time = parseInt(e["time"]);
  // e["weight"] = Math.max(Math.floor(Math.random() * 100 - 40) / 10 - 0.5, 0);
  var specialInfo = !e["weight"] ? null : {
    weight: Math.abs(e["weight"]),
    radius: 4 + 160 * Math.abs(e["weight"]),
    isneg: e["weight"] > 0
  };
  if(e["weight"]) {
    TypePool.hasWeightedEvent = true;
  }
  var cost = e["cost"] || 0;
  if(cost) {
    cost = +cost;
    if(Number.isNaN(cost)) {
      cost = 0;
    }
  }
  this.cost = function() {
    return cost;
  };

  var resultFlag = (e["flag"] || "").trim();
  var selected = false;

  var topoX = -1;
  this.topoX = function(_) {
    if(!arguments.length) return topoX;
    topoX = _;
  };

  var ixInType = -1;
  this.ixInType = function(_) {
    if(!arguments.length) return ixInType;
    ixInType = _;
  };

  var lastX = Number.NaN;
  this.lastX = function(_) {
    if(!arguments.length) return lastX;
    lastX = _;
  };
  var width = Number.NaN;
  this.width = function(_) {
    if(!arguments.length) return width;
    width = _;
  };

  var shown = true;
  this.shown = function(_) {
    if(!arguments.length) return shown;
    shown = _;
    if(!shown) {
      that.deleteEvent();
      destroyed = false;
    }
  };

  this.eq = function(otherEvent) {
    if(that === otherEvent) return true;
    if(that.getTime() !== otherEvent.getTime()) return false;
    if(that.getWeight() !== otherEvent.getWeight()) return false;
    if(that.getDesc() !== otherEvent.getDesc()) return false;
    return true;
  };

  var type = pool.addEventToType(that, e, dictionary);
  var desc = Event.eventDesc(e, type);

  if("event_id" in e) {
    pool.registerNamedEvent(e["event_id"], that);
  }
  var connections = e["connections"] || [];

  var eg_id = "";
  if("row_id" in e) {
    eg_id = e["row_id"];
    if(eg_id.length) {
      pool.registerEventGroup(eg_id, that);
    }
  }
  this.getEventGroupId = function() {
    return eg_id;
  };

  this.isFirstOfType = function() {
    return type.getCount() && type.getEventByIndex(0) === that;
  };
  this.isWeighted = function() {
    return !!specialInfo;
  };
  this.getWeight = function() {
    return specialInfo ? specialInfo.weight : 0;
  };
  this.showOnlyWeighted = function() {
    that.shown(!!specialInfo);
  };
  this.clickSelected = function() {
    var pool = that.getType().getPool();
    pool.highlightEvent(that);
  };
  this.setSelected = function(isSelected) {
    var old = selected;
    selected = !!isSelected;
    if(old != selected) {
      that.getType().getPool().updateSelection();
    }
  };
  this.isSelected = function() {
    return selected;
  };
  this.getTime = function() {
    return time;
  };
  this.getType = function() {
    return type;
  };
  this.getColor = function() {
    if(that.isSelected()) {
      return d3.rgb("darkgray");
    }
    return that.getBaseColor();
  };
  this.getBaseColor = function() {
    return that.getType().getColor(resultFlag);
  };
  this.getDesc = function() {
    return desc + " (" + that.getType().getCount() + ")";
  };
  this.getId = function() {
    return id;
  };

  var sel = null;
  var additional = null;
  var connectionsPath = null;
  var destroyed = false;
  this.select = function() {
    if(destroyed) {
      console.warn("event already destroyed");
      return null;
    }
    if(!sel) {
      var pSel = that.getType().select();
      sel = pSel.append("rect").datum(that);
    }
    return sel;
  };
  this.updateLook = function() {
    if(destroyed) {
      console.warn("event already destroyed");
      return false;
    }
    that.select().attr({
      "fill": that.getColor(),
      "stroke": that.isSelected() ? "gray" : "gray",
      "stroke-width": 0.1
    });
    if(connections.length && !connectionsPath) {
      connectionsPath = pool.select().append("g").datum(that);
    }
    if(connectionsPath) {
      var boxSize = pool.boxSize();
      var colW = boxSize[0];
      var rowH = boxSize[1];
      var ownX = pool.getXByEventTime(that) + colW * 0.5;
      var ownY = that.getType().getY() + rowH * 0.5;
      connectionsPath.selectAll("line").remove();
      if(that.shown()) {
        connections.forEach(function(con) {
          var cid = con["event_id"];
          var other = pool.getNamedEvent(cid);
          if(!other || !other.shown()) return;
          var x = pool.getXByEventTime(other) + colW * 0.5;
          var y = other.getType().getY() + rowH * 0.5;
          connectionsPath.append("line").attr({
            "stroke-width": "stroke_width" in con ? con["stroke_width"] : 4,
            "stroke": "color" in con ? con["color"] : "black",
            "stroke-linecap": "round",
            "x1": ownX,
            "y1": ownY,
            "x2": x,
            "y2": y
          });
        });
      }
    }
    return true;
  };
  this.updateAdditional = function(x, y) {
    if(!specialInfo) {
      if(additional) {
        additional.remove();
        additional = null;
      }
      return;
    }
    if(!additional) {
      var pSel = that.getType().select();
      additional = pSel.append("circle").datum(that);
      jkjs.util.toFront(additional, false);
    }
    additional.attr({
      "cx": x,
      "cy": y,
      "r": specialInfo.radius,
      "stroke-width": 1,
      "stroke": specialInfo.isneg ? "red" : "black",
      "fill": "none",
      // "opacity": 0.5
    });
  };
  this.deleteEvent = function() {
    if(sel) {
      sel.remove();
      sel = null;
    }
    if(additional) {
      additional.remove();
      additional = null;
    }
    if(connectionsPath) {
      connectionsPath.remove();
      connectionsPath = null;
    }
    destroyed = true;
  };

  this.createListEntry = function(sel) {
    sel.on("click", function(e) {
      if(d3.event.button != 0) return;
      e.clickSelected();
    });
    sel.append("div").classed("pBox", true).style({
      "background-color": function(e) {
        return e.getBaseColor();
      }
    });
    sel.append("span");
  };
  this.updateListEntry = function(sel, singleSlot, singleType) {
    var color = that.getBaseColor();
    var showSelection = that.getType().getPool().highlightEvent() === that;
    // removes all children of sel
    sel.selectAll("span").text(that.getDesc()).style({
      "background-color": showSelection ? color : null,
      "color": showSelection ? jkjs.util.getFontColor(color) : null
    });
    // TODO scroll only when necessary
    // if(singleSlot && singleType && showSelection) {
    //   sel.node().scrollIntoView(true);
    // }
  };
} // Event
Event.currentId = 0;
Event.nextId = function() {
  var id = "e" + Event.currentId;
  Event.currentId += 1;
  return id;
};
Event.eventDesc = function(e, type) {
  var add;
  if("flag" in e) {
    add = ": " + e["flag_value"];
  } else {
    add = "";
  }
  return type.getDesc() + add;
};
