/**
 * Created by krause on 2014-09-29.
 */

function TypeView(pool, sel, sortDropdownSel) {
  var that = this;
  var totalHeight = Number.NaN;
  var totalWidth = 265;

  var typeSort = null;
  var dropdown = sortDropdownSel.append("select").classed("dropdown", true).on("change", function() {
    var dd = dropdown.node();
    var s = d3.select(dd.options[dd.selectedIndex]).datum();
    that.selectSort(s);
  });
  this.addSort = function(desc, sort) {
    var g = {
      desc: desc,
      sort: sort
    };
    dropdown.append("option").datum(g).text(g.desc);
    return g;
  };
  this.selectSort = function(s) {
    typeSort = s.sort;
    dropdown.selectAll("option").each(function(g, i) {
      if(g !== s) return;
      var tmpChg = dropdown.on("change");
      dropdown.on("change", null);
      dropdown.node().selectedIndex = i;
      dropdown.on("change", tmpChg);
    });
    that.updateLists();
  };

  var selectedTypes = {};
  pool.addSelectionListener(function(es, types, singleSlot, singleType) {
    selectedTypes = types;
    that.updateLists();
  });
  sel.style({
    "display": "inline-block",
    "padding": 0,
    "width": totalWidth + "px"
  });

  this.resize = function(allowedHeight, bodyPadding) {
    totalHeight = allowedHeight;
    sel.style({
      "position": "absolute",
      "top": bodyPadding + "px",
      "right": 10 + "px",
      "width": totalWidth + "px",
      "height": totalHeight + "px"
    });
    this.updateLists();
    fingerQueue += 2;
    fingerprints();
  };

  var fingerQueue = 0;
  function fingerprints() {
    if(fingerQueue > 1) {
      fingerQueue -= 1;
      sel.selectAll("canvas.fingerprint").style({
        "display": "none"
      });
      setTimeout(fingerprints, 0);
      return;
    }
    if(fingerQueue <= 0) {
      return;
    }
    fingerQueue = 0;
    sel.selectAll("canvas.fingerprint").style({
      "display": null
    }).each(function(d) {
      var fpSel = d3.select(this);
      var pSel = d3.select(fpSel.node().parentNode);
      var types = d.types;
      var h = 14;
      var w = totalWidth - 44;
      var tw = w;
      var th = h * types.length;
      fpSel.attr({
        "width": tw,
        "height": th
      }).style({
        "position": "absolute",
        "top": 0,
        "left": 22 + "px",
        "width": tw + "px",
        "height": th + "px",
        "z-index": -1000
      });
      jkjs.util.toFront(fpSel, true);
      var ctx = fpSel.node().getContext("2d");
      ctx.globalAlpha = 1;
      ctx.clearRect(0, 0, totalWidth, totalHeight);
      ctx.save();
      types.forEach(function(type) {
        //ctx.fillStyle = "black";
        //ctx.fillText(type.getDesc(), 0, h);
        type.fillFingerprint(ctx, w, h);
        ctx.translate(0, h);
      });
      ctx.restore();
    });
  }

  this.clearLists = function() {
    sel.selectAll("div.pType").remove();
  };

  var oldTypes = [];
  var nodeRoots = [];
  var groupIx = 0;
  this.updateLists = function() {
    var groups = {};
    pool.traverseTypes(function(gid, tid, t) {
      if(!(gid in groups)) {
        groups[gid] = {
          desc: t.getRoot().getDesc(),
          types: []
        };
      }
      groups[gid].types.push(t);
    });

    var gKeys = Object.keys(groups).filter(function(_, ix) {
      return ix === groupIx;
    });
    var gCount = Object.keys(groups).length;

    function chgGroupIx(inc) {
      groupIx += inc ? 1 : -1;
      if(groupIx < 0) {
        groupIx = gCount - 1;
      }
      if(groupIx >= gCount) {
        groupIx = 0;
      }
      that.updateLists();
    }

    var pType = sel.selectAll("div.pType").data(gKeys, function(key) {
      return key;
    });
    pType.exit().remove();
    var pe = pType.enter().append("div").classed("pType", true);
    var head = pe.append("div").classed("pTypeHead", true);
    head.append("span").classed("pTypeLeft", true);
    head.append("span").classed("pTypeSpan", true).style({
      "position": "relative"
    });
    head.append("span").classed("pTypeRight", true);
    pe.append("div").classed("pTypeDiv", true);

    pType.selectAll("span.pTypeLeft").text("<").on("click", function() {
      chgGroupIx(false);
    }).style({
      "left": "10px",
      "position": "absolute",
      "cursor": "pointer",
      "text-align": "center"
    });
    pType.selectAll("span.pTypeRight").text(">").on("click", function() {
      chgGroupIx(true);
    }).style({
      "right": "10px",
      "position": "absolute",
      "cursor": "pointer",
      "text-align": "center"
    });

    pType.selectAll("div.pTypeHead").style({
      "border-radius": 4 + "px",
      "text-align": "center",
      "margin": "0 0 4px 0",
      "padding": "5px 0",
      "background-color": function(gid) {
        return pool.getGroupColor(gid);
      },
      "color": function(gid) {
        return jkjs.util.getFontColor(pool.getGroupColor(gid));
      }
    });
    pType.selectAll("span.pTypeSpan").text(function(gid) {
      return groups[gid].desc;
    }).on("click", function(gid) {
      if(d3.event.button != 0) return;
      pool.startBulkValidity();
      var state = Number.NaN;
      pool.traverseGroup(gid, function(t) {
        if(state == 0) {
          return;
        }
        var v = t.isValid();
        if(isNaN(state)) {
          state = v ? 1 : -1;
        } else if((state > 0 && !v) || (state < 0 && v)) {
          state = 0;
        }
      });
      var setV = state <= 0;
      pool.traverseGroup(gid, function(t) {
        t.setValid(setV);
      });
      pool.endBulkValidity();
    });
    var h = totalHeight / gKeys.length - 46; // 24: padding + margin + border; 22: buffer
    var divs = pType.selectAll("div.pTypeDiv").style({
      "font-size": "10px",
      "font-family": "monospace",
      "white-space": "nowrap",
      "max-height": h + "px",
      "max-width": totalWidth + "px",
      "margin": "0 0 12px 0",
      "position": "absolute"
    });

    function Node(id, type) {
      var that = this;
      var children = {};
      var childs = null;
      var descendants = null;
      var count = Number.NaN;
      var y = Number.NaN;
      var isRoot = false;
      this.isRoot = function(_) {
        if(!arguments.length) return isRoot;
        isRoot = !!_;
      };
      this.putChild = function(node) {
        var id = node.getId();
        if(that.getId() == id) {
          console.warn("tried to add itself as child", "'" + id + "'");
          return;
        }
        children[id] = node;
        childs = null;
        count = Number.NaN;
        y = Number.NaN;
      };
      this.getId = function() {
        return id;
      };
      this.getType = function() {
        return type;
      };
      this.getDesc = function() {
        return type.getDesc();
      };
      this.getName = function() {
        return type.getName();
      };
      this.getCount = function() {
        if(Number.isNaN(count)) {
          if(that.hasChildren()) {
            count = 0;
            that.getChildren().forEach(function(c) {
              count += c.getCount();
            });
          } else {
            count = type.getCount();
          }
        }
        return count;
      };
      this.getY = function() {
        if(Number.isNaN(y)) {
          y = Number.POSITIVE_INFINITY;
          that.getChildren().forEach(function(c) {
            y = Math.min(y, c.getY());
          });
        }
        return y;
      };
      this.getChildren = function() {
        if(!childs) {
          childs = Object.keys(children).map(function(c) {
            return children[c];
          });
        }
        return childs;
      };
      this.getDescendantTypes = function() {
        if(!descendants) {
          descendants = {};
          descendants[that.getId()] = that.getType();
          that.getChildren().forEach(function(c) {
            var cdt = c.getDescendantTypes();
            Object.keys(cdt).forEach(function(d) {
              descendants[d] = cdt[d];
            });
          });
        }
        return descendants;
      };
      this.hasChildren = function() {
        return that.getChildren().length > 0;
      };
      this.isExpanded = function() {
        return that.isRoot() || !that.getChildren().some(function(c) {
          return c.getType().hasRealProxy();
        });
      };
      this.preorder = function(cb, level, onlyVisible) {
        cb(level, that, that.hasChildren(), that.isExpanded());
        if(that.hasChildren() && (!onlyVisible || that.isExpanded())) {
          var cs = that.getChildren();
          typeSort && cs.sort(function(a, b) {
            return typeSort(a, b);
          });
          cs.forEach(function(n) {
            n.preorder(cb, level + 1, onlyVisible);
          });
        }
      };
      this.setExpanded = function(expand) {
        toggle(this, !expand);
      }
    } // Node

    var roots = {};
    var nodeMap = {};
    function buildHierarchy(type) {
      var g = type.getGroup();
      if(!(g in nodeMap)) {
        nodeMap[g] = {};
      }
      var nm = nodeMap[g];
      var t = type;
      var node = null;
      while(t) {
        var id = t.getTypeId();
        var p = id in nm ? nm[id] : new Node(id, t);
        if(node) {
          p.putChild(node);
        }
        if(id == "" && !(g in roots)) {
          p.isRoot(true);
          roots[g] = p;
        }
        if(!(id in nm)) {
          nm[id] = p;
        } else {
          break;
        }
        node = p;
        t = t.getParent();
      }
      if(!(g in roots)) {
        console.warn("no real root found!");
        roots[g] = new Node("", {
          "getGroup": function() {
            return g;
          },
          "getTypeId": function() {
            return "";
          }
        });
        roots[g].isRoot(true);
        node && roots[g].putChild(node);
      }
    }

    Object.keys(groups).forEach(function(gid) {
      groups[gid].types.forEach(function(type) {
        buildHierarchy(type);
      });
    });

    function toggle(node, collapse) {
      var type = node.getType();
      pool.startBulkValidity();
      node.preorder(function(level, n) {
        if(!level) return;
        var t = n.getType();
        if(collapse) {
          t.proxyType(type);
        } else {
          t.proxyType(t);
        }
      }, 0, false);
      pool.endBulkValidity();
    }

    var fingerprintTypes = [];
    var updateFingerprints = false;
    divs.selectAll("div.pT").remove();
    divs.each(function(gid) {
      var pT = d3.select(this);
      var types = [];
      roots[gid].preorder(function(level, node, isInner, isExpanded) {
        var type = node.getType();
        if(type.getTypeId() == "") {
          return;
        }
        updateFingerprints = type.setFingerprintTypes(node.getDescendantTypes()) || updateFingerprints;
        fingerprintTypes.push(type.getTypeId());
        var div = pT.append("div").classed("pT", true).datum(type);
        if("createListEntry" in type) {
          types.push(type);
          var objs = type.createListEntry(div, level, isInner, isExpanded);
          objs["space"].on("click", function() {
            toggle(node, isExpanded);
            that.updateLists();
          });
        }
      }, 0, true);
      var fpSel = pT.selectAll("canvas.fingerprint").data([{
        id: gid,
        types: types
      }], function(d) {
        return d.id;
      });
      fpSel.exit().remove();
      fpSel.enter().append("canvas").classed("fingerprint", true);
    });

    divs.selectAll("div.pT").each(function(t) {
      var div = d3.select(this);
      var pt = t.proxyType();
      var hasSelected = pt.getId() in selectedTypes;
      while(pt.getParent() && !hasSelected) {
        pt = pt.getParent();
        hasSelected = pt.getId() in selectedTypes;
      }
      var onlyOneTypeSelected = Object.keys(selectedTypes).length == 1;
      if("updateListEntry" in t) {
        t.updateListEntry(div, hasSelected, onlyOneTypeSelected);
      }
      // TODO detect when it's not a manual selection and then scroll
      //if(hasSelected && onlyOneTypeSelected) {
      //  div.node().scrollIntoView(true);
      //}
    });

    nodeRoots = Object.keys(roots).map(function(r) {
      return roots[r];
    });

    fingerprintTypes.sort();
    if(!updateFingerprints) {
      if(fingerprintTypes.length === oldTypes.length) {
        for(var ix = 0;ix < oldTypes.length;ix += 1) {
          if(oldTypes[ix] !== fingerprintTypes[ix]) {
            updateFingerprints = true;
            break;
          }
        }
      } else {
        updateFingerprints = true;
      }
    }
    oldTypes = fingerprintTypes;

    if(updateFingerprints) {
      fingerQueue += 2;
      fingerprints();
    }
  };
  this.getNodeRoots = function() {
    return nodeRoots;
  };
} // EventView
