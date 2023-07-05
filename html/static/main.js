// Main

function fetchData(){
    var xmlhttp = new XMLHttpRequest();
    xmlhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            var data = JSON.parse(this.responseText);
            console.log(data);
            updateResponseTimePlot(data['edge_response_times'], 'response_times');
            updateResponseTimePlot(data['origin_response_times'], 'origin_response_times');
        }
    };

    data = xmlhttp.open("GET", "output.json", true);
    xmlhttp.send()
}


function updateResponseTimePlot(data, dest){
    regions = {}

    data.forEach(function(val){
        // Instantiate the object if needed
        if (!(val["region"] in regions)){
            regions[val["region"]] = {
                 x: [],
                 y: [],
                 name: val["region"],
                 mode: "lines"
            }
        }

        // Push data in
        regions[val["region"]].x.push(val['time'])
        regions[val["region"]].y.push(val['response_time'])

    });

    odata = []
    for ([region, val] of Object.entries(regions)){
        odata.push(val);
    }
    console.log(odata)
    Plotly.newPlot(dest, odata)
}

fetchData()
