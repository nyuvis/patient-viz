/**
 * Created by krause on 2015-04-27.
 */

function Histogram(svg) {
  var that = this;
  var values = [];
  var max = 1;
  var colors = ["#eee", "#bbb", "#777", "#444", "#000"];
  var yLabelsLeft = svg.append("g").classed("yAxisClass", true);
  var yLabelsRight = svg.append("g").classed("yAxisClass", true);
  var g = svg.append("g").attr({
    "transform": "scale(1 1) translate(0 0)"
  });
  var lineSel = g.append("g");
  var timeMap = function(t) {
    return 0;
  };
  var yMap = function(v) {
    return 0;
  };

  this.mapping = function(m) {
    if(!arguments.length) return [ timeMap, yMap ];
    timeMap = m[0];
    yMap = m[1];
    that.update();
  };
  this.hasContent = function() {
    return !!values.length;
  };
  this.values = function(v) {
    if(!arguments.length) return values;
    max = Number.NEGATIVE_INFINITY;
    v.forEach(function(a) {
      var y = a[1];
      if(y > max) max = y;
    });
    if(!Number.isFinite(max) || !max) {
      max = 1;
    }
    values = v.map(function(a) {
      return [ a[0], a[1] ];
    });
    values.sort(function(a, b) {
      return d3.ascending(a[0], b[0]);
    });
    that.update();
  };
  var useLog = true;
  var yc = useLog ? d3.scale.log() : d3.scale.linear();
  this.update = function() {
    yc.domain([ useLog ? 1 : 0, max ]);
    yc.range([ yMap(0), yMap(1) ]);
    var valueMap = {};
    var times = values.map(function(v) {
      valueMap[v[0]] = v[1];
      return v[0];
    });
    times.sort(d3.ascending);
    var rects = g.selectAll("rect.hist").data(times, function(t) {
      return t;
    });
    rects.exit().remove();
    rects.enter().append("rect").classed("hist", true).attr({
      "stroke": "black",
      "stroke-width": 0.2
    });
    var smallestWidth = Number.POSITIVE_INFINITY;
    rects.each(function(t, ix) {
      if(ix + 1 < times.length) {
        var w = timeMap(times[ix + 1]) - timeMap(t);
        smallestWidth = Math.min(smallestWidth, w);
      }
    });
    rects.attr({
      "x": function(t) {
        return timeMap(t);
      },
      "width": smallestWidth,
      "y": function(t) {
        if(useLog && valueMap[t] < 1) return yMap(0);
        return yc(valueMap[t]);
      },
      "height": function(t) {
        if(useLog && valueMap[t] < 1) return 0;
        return yMap(0) - yc(valueMap[t]);
      },
      "fill": function(t) {
        var bucket = Math.max(Math.min(Math.floor(Math.log10(valueMap[t])), colors.length), 0);
        return colors[bucket];
      }
    });
    smallestWidth > 0 || console.warn("smallest width is zero");

    var yAxisLeft = d3.svg.axis();
    yAxisLeft.orient("right");
    yAxisLeft.scale(yc);
    useLog && yAxisLeft.ticks(1, 10);
    yLabelsLeft.call(yAxisLeft);
    jkjs.util.toFront(yLabelsLeft, true);

    var yAxisRight = d3.svg.axis();
    yAxisRight.orient("left");
    yAxisRight.scale(yc);
    useLog && yAxisRight.ticks(1, 10);
    yLabelsRight.call(yAxisRight);
    jkjs.util.toFront(yLabelsRight, true);

    var horLines = [];
    if(useLog) {
      var l = 10;
      while(l < max) {
        horLines.push(l);
        l *= 10;
      }
    } else {
      yLabelsLeft.selectAll("g.tick").each(function(l) {
        horLines.push(l);
      });
    }
    var horSel = lineSel.selectAll("line.hor_line").data(horLines, function(l) { return l; });
    horSel.exit().remove();
    horSel.enter().append("line").classed("hor_line", true);
    horSel.attr({
      "stroke": "lightgray",
      "x1": -0.25 * jkjs.util.BIG_NUMBER,
      "x2": 0.5 * jkjs.util.BIG_NUMBER,
      "y1": function(l) {
        return yc(l);
      },
      "y2": function(l) {
        return yc(l);
      }
    });

    if(!values.length) {
      yLabelsLeft.style({
        "opacity": 0
      });
      yLabelsRight.style({
        "opacity": 0
      });
    } else {
      yLabelsLeft.style({
        "opacity": null
      });
      yLabelsRight.style({
        "opacity": null
      });
    }
  };
  this.updateWidth = function(newWidth) {
    yLabelsRight.attr({
      "transform": "translate(" + newWidth + " 0)"
    });
  };
  this.getG = function() {
    return g;
  };
}; // Histogram
