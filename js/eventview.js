/**
 * Created by krause on 2014-09-29.
 */

function EventView(sel) {
  var that = this;
  var totalHeight = Number.NaN;
  var totalWidth = 265;
  var singleSlot = false;
  var singleType = false;
  var events = [];
  var full = sel.append("div");
  var header = full.append("span").text("Selection").style({
    "font-weight": 500
  });
  var list = full.append("div").style({
    "overflow": "auto",
    "max-height": "200px"
  });
  var sortAndGroup = null;
  var dropdown = header.append("select").classed("dropdown", true).on("change", function() {
    var dd = dropdown.node();
    var sag = d3.select(dd.options[dd.selectedIndex]).datum();
    that.selectSortAndGroup(sag);
  }).style({
    "position": "absolute",
    "right": "14px"
  });
  // TODO
  this.resize = function(allowedHeight, bodyPadding) {
    full.style({
      "width": totalWidth + "px",
      "height": allowedHeight + "px"
    });
    var head = header.node().offsetHeight;
    list.style({
      "max-height": (allowedHeight - head - 10) + "px"
    });
  };

  this.connectPool = function(pool) {
    pool.addSelectionListener(function(es, types, singleSlot, singleType) {
      if(es.length && singleSlot) {
        var tmp = [];
        pool.traverseEventsForEventTime(es[0], function(e) {
          tmp.push(e);
        });
        that.setEvents(tmp, singleSlot, singleType);
      } else {
        that.setEvents(es, singleSlot, singleType);
      }
    });
    pool.addHighlightListener(function() {
      that.updateEntries();
    });
  };

  this.setEvents = function(es, ss, st) {
    events = es;
    singleSlot = ss;
    singleType = st;
    that.updateList();
  };

  this.updateList = function() {
    var groups;
    if(sortAndGroup && sortAndGroup.group) {
      var set = {};
      events.forEach(function(e) {
        var g = sortAndGroup.group(e);
        if(!(g.id in set)) {
          set[g.id] = {
            id: g.id,
            desc: g.desc,
            events: []
          };
        }
        set[g.id].events.push(e);
      });
      groups = [];
      Object.keys(set).sort().forEach(function(id) {
        groups.push(set[id]);
      });
    } else {
      groups = [{
        id: "events",
        desc: "Events",
        events: events
      }];
    }

    var gs = list.selectAll("p.eP").data(groups, function(g) {
      return g.id;
    }).order();
    gs.exit().remove();
    var gsE = gs.enter().append("p").classed("eP", true);
    gsE.append("h5").classed("eHead", true);
    gsE.append("ul").classed({
      "list-unstyled": true,
      "eUl": true
    }).style({
      "font-size": "10px",
      "font-family": "monospace",
      "white-space": "nowrap"
    });

    // groups won't get properly propagated to
    // elements created in the enter section
    function propagateGroup(g) {
      groups.forEach(function(ref) {
        if(ref.id !== g.id) return;
        g.events = ref.events;
        g.desc = ref.desc;
      });
    };

    var groupHeaders = gs.selectAll("h5.eHead");
    groupHeaders.each(propagateGroup);
    groupHeaders.text(function(g) {
      return g.desc;
    });

    var eu = gs.selectAll("ul.eUl").each(propagateGroup);
    var es = eu.selectAll("li.pElem").data(function(g) {
      return g.events;
    }, function(e) {
      return e.getId();
    });
    es.exit().remove();
    es.enter().append("li").classed("pElem", true).each(function(e) {
      var li = d3.select(this);
      e.createListEntry(li);
    });
    if(sortAndGroup && sortAndGroup.sort) {
      es.sort(sortAndGroup.sort);
    }
    that.updateEntries();
  };
  this.updateEntries = function() {
    list.selectAll("li.pElem").each(function(e) {
      var li = d3.select(this);
      e.updateListEntry(li, singleSlot, singleType);
    });
  };

  this.addSortAndGroup = function(desc, sort, group) {
    // TODO
    var g = {
      desc: desc,
      sort: sort,
      group: group
    };
    dropdown.append("option").datum(g).text(g.desc);
    return g;
  };
  this.selectSortAndGroup = function(sg) {
    sortAndGroup = sg;
    // TODO
    that.updateList();
  };
} // EventView
