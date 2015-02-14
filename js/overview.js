/**
 * Created by krause on 2014-09-25.
 */

function Overview(sel, handler) {
  var that = this;
  var maxHeight = 100;
  var initW = handler.getSize().width;
  var svg = sel.append("svg").style({
    "width": initW + "px"
  });
  svg.on("dblclick", function() {
    var zui = handler.getZUI();
    zui.showAll(true);
  });
  var drag = d3.behavior.drag().on("drag", function() {
    var box = handler.getBox();
    if(!box) return;
    var size = handler.getSize();
    var zui = handler.getZUI();
    var scale = zui.getScale() / that.getScaleFor(size.width, box);
    var dx = -d3.event.dx * scale;
    var dy = -d3.event.dy * scale;
    zui.move(dx, dy, false);
  });
  svg.call(drag);
  this.getSVG = function() {
    return svg;
  };
  var shadowRect = svg.append("rect").attr({
    "x": 0,
    "y": 0,
    "width": initW,
    "stroke": "black",
    "stroke-width": 1,
    "fill": "none"
  });
  var camRect = null;
  var shadow = null;

  this.clearShadow = function() {
    if(shadow) {
      shadow.remove();
      shadow = null;
    }
  };
  this.onBoxUpdate = function() {
    var box = handler.getBox();
    if(!box) return;
    if(!shadow) {
      shadow = svg.append("use").attr({
        "xlink:href": "#mainG"
      });
    }
    if(!camRect) {
      camRect = svg.append("rect").attr({
        "stroke": "black",
        "stroke-width": 2,
        "fill": "none"
      });
    }
    var size = handler.getSize();
    var ss = that.getScaleFor(size.width, box);
    var sh = box.height * ss;
    shadow.attr({
      "transform": "scale(" + ss + ")"
    });
    svg.style({
      "height": sh + "px"
    });
    shadowRect.attr({
      "height": sh
    });
  };

  this.onSizeUpdate = function() {
    var size = handler.getSize();
    svg.style({
      "width": size.width + "px"
    });
    shadowRect.attr({
      "width": size.width
    });
  };

  this.getScaleFor = function(width, box) {
    var ss = width / box.width;
    var sh = Math.min(box.height * ss, maxHeight);
    return sh / Math.max(box.height, 1);
  };
  this.getHeightForWidth = function(width) {
    var box = handler.getBox();
    if(!box) return width;
    return Math.ceil(box.height * that.getScaleFor(width, box));
  };

  this.updateCameraRect = function(canvasRect, visRect, smooth) {
    if(!camRect) return;
    var size = handler.getSize();
    var ss = that.getScaleFor(size.width, canvasRect);
    var tgt = jkjs.zui.asTransition(camRect, smooth);
    tgt.attr({
      "x": visRect.x * ss,
      "y": visRect.y * ss,
      "width": visRect.width * ss,
      "height": visRect.height * ss
    });
  }

} // Overview
