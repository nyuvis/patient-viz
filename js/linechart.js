/**
 * Created by krause on 2014-11-06.
 */

function Linechart(svg) {
  var that = this;
  var values = [];
  var min = 0;
  var max = 1;
  var yLabelsLeft = svg.append("g").classed("yAxisClass", true);
  var yLabelsRight = svg.append("g").classed("yAxisClass", true);
  var g = svg.append("g").attr({
    "transform": "scale(1 1) translate(0 0)"
  });
  var path = g.append("path").attr({
    "fill": "transparent",
    "stroke": "black",
    "stroke-width": "2px"
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
    that.updatePath();
  };
  this.hasContent = function() {
    return !!values.length;
  };
  this.values = function(v) {
    if(!arguments.length) return values;
    min = Number.POSITIVE_INFINITY;
    max = Number.NEGATIVE_INFINITY;
    v.forEach(function(a) {
      var y = a[1];
      if(y < min) min = y;
      if(y > max) max = y;
    });
    if(!Number.isFinite(min) || !Number.isFinite(max)) {
      min = 0;
      max = 1;
    }
    values = v.map(function(a) {
      return [ a[0], (a[1] - min) / (max - min) ];
    });
    values.sort(function(a, b) {
      return d3.ascending(a[0], b[0]);
    });
    that.updatePath();
  };
  this.updatePath = function() {
    var p = new jkjs.Path();
    values.forEach(function(v) {
      var x = timeMap(v[0]);
      var y = yMap(v[1]);
      if(p.isEmpty()) {
        p.move(x, y);
      } else {
        p.line(x, y);
      }
    });
    path.attr({
      "d": p
    });
    var yAxisLeft = d3.svg.axis();
    var yAxisRight = d3.svg.axis();
    yAxisLeft.orient("right");
    yAxisRight.orient("left");
    var yc = d3.scale.linear();
    yc.domain([ min, max ]);
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
}; // Linechart
