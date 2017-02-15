function drawChordForConcept(service_url, uri) {
    $('#graph').empty();
    $("#loading").show();
    $.get(service_url, {'type': 'concepts', 'uri': uri }, function(data) {
                $("#loading").hide();
                if (data) {
                        drawChord(service_url, data.matrix, data.concepts, "#graph");
                } else {
                        $("#noresponse").show();
                }

            });
}




function drawChord(service_url, matrix, concepts, target) {
    var width = 900,
    height = 900,
    outerRadius = Math.min(width-150, height-150) / 2 - 10,
    innerRadius = outerRadius - 24;

    var formatPercent = d3.format(".1%");

    var arc = d3.svg.arc()
        .innerRadius(innerRadius)
        .outerRadius(outerRadius);

    var layout = d3.layout.chord()
        .padding(0.04)
        .sortSubgroups(d3.descending)
        .sortChords(d3.ascending);

    var path = d3.svg.chord()
        .radius(innerRadius);

    var svg = d3.select(target).append("svg")
        .attr("width", width)
        .attr("height", height)
      .append("g")
        .attr("id", "circle")
        .attr("transform", "translate(" + width / 2 + "," + height / 2 + ")");

    svg.append("circle")
        .attr("r", outerRadius);






    // Compute the chord layout.
    layout.matrix(matrix);

    // Add a group per neighborhood.
    var group = svg.selectAll(".group")
        .data(layout.groups)
      .enter().append("g")
        .attr("class", "group")
        .on("mouseover", mouseover)
        .on("click", function(d,i){ click(concepts[i]); });

    // Add a mouseover title.
    group.append("title").text(function(d, i) {
      return concepts[i].name + ": " + formatPercent(d.value) + " of origins";

    });

    // Add the group arc.
    var groupPath = group.append("path")
        .attr("id", function(d, i) { return "group" + i; })
        .attr("d", arc)
        .style("fill", function(d, i) { return concepts[i].color; });

    // Add a text label.
    //var groupText = group.append("text")
    //    .attr("x", 6)
    //    .attr("dy", 15);
    //
    //groupText.append("textPath")
    //    .attr("xlink:href", function(d, i) { return "#group" + i; })
    //    .text(function(d, i) { return concepts[i].name; });

    var groupText = group.append("text")
        .each(function(d) { d.angle = (d.startAngle + d.endAngle) / 2; })
        .attr("dy", ".35em")
        .attr("text-anchor", function(d) { return d.angle > Math.PI ? "end" : null; })
        .attr("transform", function(d) {
          return "rotate(" + (d.angle * 180 / Math.PI - 90) + ")"
              + "translate(" + (innerRadius + 26) + ")"
              + (d.angle > Math.PI ? "rotate(180)" : "");
        })
        .attr("class","chord-label")
        .text(function(d, i) { return concepts[i].name; });


    // Remove the labels that don't fit. :(
    //groupText.filter(function(d, i) { return groupPath[0][i].getTotalLength() / 2  < this.getComputedTextLength(); }) // Was: -16 !
    //    .remove();

    // Add the chords.
    var chord = svg.selectAll(".chord")
        .data(layout.chords)
      .enter().append("path")
        .attr("class", "chord")
        .style("fill", function(d) { return concepts[d.source.index].color; })
        .attr("d", path);

    // Add an elaborate mouseover title for each chord.
    chord.append("title").text(function(d) {
      return concepts[d.source.index].name
          + " → " + concepts[d.target.index].name
          + ": " + formatPercent(d.source.value)
          + "\n" + concepts[d.target.index].name
          + " → " + concepts[d.source.index].name
          + ": " + formatPercent(d.target.value);
    });

    function mouseover(d, i) {
      chord.classed("fade", function(p) {
        return p.source.index != i
            && p.target.index != i;
      });
    }

    function click(concept) {
        console.log(concept)
        drawChordForConcept(service_url, concept.uri);
    }
}
