/**
 * Created by krause on 2014-03-05.
 */

function EventClusterer() {
  var that = this;
  var distance = function(vecA, vecB) {
    return jkjs.stat.edit_distances.hamming(vecA, vecB);
  };
  var threshold = 5;
  var minCluster = 3;
  var clusterTypes = [];

  this.distance = function(_) {
    if(!arguments.length) return distance;
    distance = _;
    clusterTypes = [];
    return that;
  };
  this.threshold = function(_) {
    if(!arguments.length) return threshold;
    threshold = _;
    clusterTypes = [];
    return that;
  };
  this.minCluster = function(_) {
    if(!arguments.length) return minCluster;
    minCluster = _;
    clusterTypes = [];
    return that;
  };

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
    return types;
  }

  this.compute = function(pool) {
    clusterTypes = computeRowClusters(pool, distance, threshold, minCluster);
    return that;
  };

  function assignProxies(clusterTypes) {
    // assign proxies
    console.log("assign proxies");
    pool.startBulkValidity();
    clusterTypes.forEach(function(obj) {
      obj.type.proxyType(obj.cluster);
    });
    pool.endBulkValidity();
  }

  this.assignProxies = function() {
    assignProxies(clusterTypes);
    return that;
  };

} // EventClusterer
