/**
 * Created by krause on 2015-04-27.
 */

function Histogram(svg) {
  var that = this;
  var values = [];
  var max = 1;
  var yLabelsLeft = svg.append("g").classed("yAxisClass", true);
  var yLabelsRight = svg.append("g").classed("yAxisClass", true);
  var g = svg.append("g").attr({
    "transform": "scale(1 1) translate(0 0)"
  });
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
      return [ a[0], a[1] / max ];
    });
    values.sort(function(a, b) {
      return d3.ascending(a[0], b[0]);
    });
    that.update();
  };
  this.update = function() {
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
      "fill": "lightgray",
      "stroke": "black"
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
        return yMap(valueMap[t]);
      },
      "height": function(t) {
        return yMap(0) - yMap(valueMap[t]);
      }
    });
    smallestWidth > 0 || console.warn("smallest width is zero");
    var yAxisLeft = d3.svg.axis();
    var yAxisRight = d3.svg.axis();
    yAxisLeft.orient("right");
    yAxisRight.orient("left");
    var yc = d3.scale.linear();
    yc.domain([ 0, max ]);
    yc.range([ yMap(0), yMap(1) ]);
    yAxisLeft.scale(yc);
    yAxisRight.scale(yc);
    yLabelsLeft.call(yAxisLeft);
    yLabelsRight.call(yAxisRight);
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
