function drawSunburstForConcept(service_url, uri) {
    $('#graphIn').empty();
    $('#graphOut').empty();
    $('#title').empty();
    // $('#graphOut').empty()
    $("#loading").show();
    console.log('loading...');
    $.get(service_url, {
        'uri': uri
    }, function(data) {
        $("#loading").hide();
        console.log('done loading...');
        console.log(data);

        $("#title").html(uri);

        if (data) {
            if (data.outgoing.hasOwnProperty('children') && data.outgoing.children.length > 0) {
                console.log('calling outgoing');
                console.log(data.outgoing.children);
                var tree = sortChildren(data.outgoing);
                drawSunburst(service_url, tree, "#graphOut", "relations from");
            } else {
                $("#graphOut").html("<div class='alert alert-warning'>No <span class='badge'>relations from</span> this resource");
            }
            if (data.incoming.hasOwnProperty('children') && data.incoming.children.length > 0) {
                console.log('calling incoming');
                var tree = sortChildren(data.incoming);
                drawSunburst(service_url, tree, "#graphIn", "relations to");
            } else {
                $("#graphIn").html("<div class='alert alert-warning'>No <span class='badge'>relations to</span> this resource");
            }

        } else {
            $("#noresponse").show();
        }

    });
}

function sortChildren(tree) {
    _.each(tree.children, function(item, key) {
        sortedChildren = _.sortBy(item.children, function(o) {
            return o.name.toLowerCase();
        });
        tree.children[key].children = sortedChildren;
    });
    return tree;
}


function drawSunburst(service_url, root, target, inorout) {
    var width = 486,
        height = 378,
        radius = Math.min(width, height) / 2,
        color = d3.scale.category20c();



    var svg = d3.select(target).append("svg")
        .attr("width", width)
        .attr("height", height)
        .append("g")
        .attr("transform", "translate(" + width / 2 + "," + height * 0.52 + ")");

    var partition = d3.layout.partition()
        .sort(null)
        .size([2 * Math.PI, radius * radius])
        .value(function(d) {
            return 1;
        });




    var arc = d3.svg.arc()
        .startAngle(function(d) {
            return d.x;
        })
        .endAngle(function(d) {
            return d.x + d.dx;
        })
        .innerRadius(function(d) {
            return Math.sqrt(d.y);
        })
        .outerRadius(function(d) {
            return Math.sqrt(d.y + d.dy);
        });


    var path = svg.datum(root).selectAll("path")
        .data(partition.nodes)
        .enter().append("path")
        .attr("display", function(d) {
            return d.depth ? null : "none";
        }) // hide inner ring
        .attr("d", arc)
        .style("stroke", "#fff")
        .style("fill", function(d) {
            return color((d.children ? d : d.parent).name);
        })
        .style("fill-rule", "evenodd")
        .on("mouseover", update_legend)
        .on("mouseout", remove_legend)
        .on("click", function(d) {
            setTimeout(function() {
                handleClick(service_url, d);
            }, 10);
        })
        .each(stash);


    var burst = d3.selectAll("input").on("change", function change() {
        var value = this.value === "count" ?
            function() {
                return 1;
            } :
            function(d) {
                return d.size;
            };

        path
            .data(partition.value(value).nodes)
            .transition()
            .duration(1500)
            .attrTween("d", arcTween);
    });


    svg.select("g").append("svg:text")
        .style("font-size", "4em")
        .style("font-weight", "bold")
        .text(function(d) {
            return root;
        });


    var center = svg.append("g");

    center.append("rect")
        .attr("rx", "10px")
        .attr("ry", "10px")
        .attr("x", -10)
        .attr("y", -14)
        .attr("fill", "#008cba")
        .attr("width", 10)
        .attr("height", 20);

    center.append("text")
        .text(inorout)
        .style("fill", "white")
        .classed("inorout", true);

    center.selectAll('rect')
        .attr("width", function(d) {
            return this.parentNode.getBBox().width + 10;
        })

    // Stash the old values for transition.
    function stash(d) {
        d.x0 = d.x;
        d.dx0 = d.dx;
    }

    // Interpolate the arcs in data space.
    function arcTween(a) {
        var i = d3.interpolate({
            x: a.x0,
            dx: a.dx0
        }, a);
        return function(t) {
            var b = i(t);
            a.x0 = b.x;
            a.dx0 = b.dx;
            return arc(b);
        };


    }

    var legend = d3.select("#legend")

    function update_legend(d) {
        legend.html("<p>" + d.name + "</p>")
        legend.transition().duration(200).style("opacity", "1");
    }

    function remove_legend(d) {
        legend.transition().duration(1000).style("opacity", "0");
    }

    function handleClick(service_url, d) {
        console.log(d);
        console.log("Waiting 1 sec before calling the draw function...");
        drawSunburstForConcept(service_url, d.name);
    }


    d3.select(self.frameElement).style("height", height + "px");
}
