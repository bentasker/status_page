// Main

function fetchData(){


    class_map = {
            "Up" : "state-up",
            "Mostly Up" : "state-mostlyup",
            "Degraded": "state-degraded",
            "Down": "state-down"
    }


    var xmlhttp = new XMLHttpRequest();
    xmlhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            var data = JSON.parse(this.responseText);
            console.log(data);
            
            updateServicesTable(data['services'], class_map)
            updateResponseTimePlot(data['edge_response_times'], 'response_times');
            updateResponseTimePlot(data['origin_response_times'], 'origin_response_times');
            updateResponsesTables(data['edge_responses_by_region'], 'edge_response_by_region')
            updateResponsesTables(data['origin_responses_by_region'], 'origin_response_by_region')

            var es = document.getElementById('edgestatus')
            es.innerText = data['edge_status'];
            es.className = class_map[data['edge_status']];

            var os = document.getElementById('originstatus')
            os.innerText = data['origin_status'];
            os.className = class_map[data['origin_status']];
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


function updateResponsesTables(data, dest){
    // Plotly works in columns, define a list for each
    regions = []
    mins = []
    maxs = []
    means = []
    perc = []

    for (var i=0; i<data.length; i++){
        console.log(data[i])
        regions.push(data[i].region);
        mins.push(data[i].min.toFixed(2));
        maxs.push(data[i].max.toFixed(2));
        means.push(data[i].mean.toFixed(2));
        perc.push(data[i].p95.toFixed(2));
    }


    var dataopts = [{
        type: 'table',
        header : {
            values: [
                ["<b>Region</b>"],
                ["<b>Min (ms)</b>"],
                ["<b>Max (ms)</b>"],
                ["<b>Mean (ms)</b>"],
                ["<b>P95 (ms)</b>"]
            ],
            align: "center",
            line: {width: 1},
            fill: {color: "grey"},
            font: {family: "Arial", size: 12, color: "white"}
        },
        cells: {
            values: [regions, mins, maxs, means, perc],
            align: "center",
            line: {color: "black", width: 1},
            font: {family: "Arial", size: 11, color: ["black"]}
        }
    }]

    Plotly.newPlot(dest, dataopts);
}

function updateServicesTable(services, class_map){
    
    ele = document.getElementById('servicestatuses');
    ele.innerHTML = ''
    
    t = document.createElement('table')
    tr = document.createElement('tr')
    th = document.createElement('th')
    th.innerText = "Service"
    tr.appendChild(th)
    th = document.createElement('th')
    th.innerText = "Status"
    tr.appendChild(th)
    t.appendChild(tr)
    
    for (var i=0; i<services.length; i++){
        tr = document.createElement('tr')
        td = document.createElement('td')
        td.innerText = services[i][0];
        tr.appendChild(td)
        
        td = document.createElement('td')
        td.className = class_map[services[i][1]];
        td.innerText = services[i][1];
        tr.appendChild(td)
        
        t.appendChild(tr);
    }
    
    ele.appendChild(t);
}


fetchData()
