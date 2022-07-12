/* API Functions */
function initdb(url, username) {
    $.get(url+"initdb" , {user: username});
    }

function toggle_classes(url, username){
    if (!window.loaded_data){
    $.get(url+"getall", {user: username}, function(data){
        console.log('Getting data from server');
        for (i=0; i < data.names.length; i++) {
            var val = parseInt(data.classes[i])
            var tcoords = getCoords(parseInt(data.vx[i]),parseInt(data.vy[i]), window.tileSize);
            window.classifiedTiles[data.names[i]] = {
                'class'  : val,
                'polygon': L.polygon(tcoords, {color: window.colors[val],  fillOpacity: 0.12}).bindTooltip(window.classesName[val]) };
            map.removeLayer(window.classifiedTiles[data.names[i]].polygon);
            map.addLayer(window.classifiedTiles[data.names[i]].polygon);
        };
        delete data;
        window.loaded_data = true;
        window.toggle_on = true;
        });
    }
    else {
        console.log(window.toggle_on);
        if (window.toggle_on) {
            for (key in window.classifiedTiles) { map.removeLayer(window.classifiedTiles[key].polygon);}
        }
        else {
            for (key in window.classifiedTiles) { map.addLayer(window.classifiedTiles[key].polygon);}
        };
        window.toggle_on = !window.toggle_on;
    }
};

function random(url, username) {
    window.loaded_data = false;
    $.get(url+"random" , {user: username});
    location.reload(true);
    map.removeLayer(layer);
    map.addLayer(layer);
    layer.redraw();
    }

function filter(url, username) {
    var check = '';
    window.checked = [];
    for (i=0; i<10; i++) {
        var temp = document.getElementById("checkbox_"+i);
        if (temp) {
            if (temp.checked){ check += i+','; window.checked.push(i);}
        }
    };
    var temp = document.getElementById("checkbox_noclass");
    if (temp.checked){ check += -1+',';}

    $.get(url+"filter", {user:username, checked:check}, function(data){
        map.removeLayer(layer);
        map.addLayer(layer);
        layer.redraw();
        location.reload(true);
        });
}

function redraw(url, username) {
    console.log( url );
    $.get(url+"redraw", {user: username}, function(){
     location.reload(true);
        });
     map.removeLayer(layer);
     map.addLayer(layer);
     layer.redraw();
     }

    
function reset(url, username) {
    $.get(url+"reset", {user: username}, function(){
        location.reload(true);
    });
    map.removeLayer(layer);
    map.addLayer(layer);
    layer.redraw();
}

function sort(url, username) {
    $.get(url+"sort", {user: username});
    layer.redraw();
}

/**********************/
 
/* Keyboard mapping*/
function keyboardf(event){
    //console.log(event.originalEvent.keyCode);
    //event.originalEvent.preventDefault();
    //event.originalEvent.stopPropagation();
    if (event.originalEvent.keyCode == 119) {
      vy = vy-1;
      selectTile(vx,vy,tileSize,zz);
      var shift = -1*tileSize/Math.pow(2,map.getMaxZoom()-map.getZoom());
      map.panBy(L.point(0,shift));
    };
    if (event.originalEvent.keyCode == 97) {
      vx = vx-1;
      selectTile(vx,vy,tileSize,zz);
      var shift = -1*tileSize/Math.pow(2,map.getMaxZoom()-map.getZoom());
      map.panBy(L.point(shift,0));
    };
    if (event.originalEvent.keyCode == 115) {
      vy = vy+1;
      selectTile(vx,vy,tileSize,zz);
      var shift = 1*tileSize/Math.pow(2,map.getMaxZoom()-map.getZoom());
      map.panBy(L.point(0,shift));
    };
    if (event.originalEvent.keyCode == 100) {
      vx = vx+1;
      selectTile(vx,vy,tileSize,zz);
      var shift = 1*tileSize/Math.pow(2,map.getMaxZoom()-map.getZoom());
      map.panBy(L.point(shift,0));
    };
    if (event.originalEvent.key == 'c') {clear_selected();};
    if (event.originalEvent.key == 't') {toggleClasses.button.click();};
    if (event.originalEvent.key == 'f') {map.toggleFullscreen();};
    if (event.originalEvent.key == 'h') {
      if (window.help_on) {sideHelp._animate(sideHelp._menu, -300, 0, true, true, 30);}
      else {sideHelp._animate(sideHelp._menu, 0, -300, false, true, 30)}
      window.help_on = !window.help_on;
    };
    if (event.originalEvent.key == '0') {custom(0);};
    if (event.originalEvent.key == '1') {custom(1);};
    if (event.originalEvent.key == '2') {custom(2);};
    if (event.originalEvent.key == '3') {custom(3);};
    if (event.originalEvent.key == '4') {custom(4);};
    if (event.originalEvent.key == '5') {custom(5);};
    if (event.originalEvent.key == '6') {custom(6);};
    if (event.originalEvent.key == '7') {custom(7);};
    if (event.originalEvent.key == '8') {custom(8);};
    if (event.originalEvent.key == '9') {custom(9);};
  };
/**********************/


/* Search functions */
function doSearch(url, username){
let temp = document.getElementById("mySearch");
let qq = temp.value;
$.get(url+"query", {user: username, query:qq}, function(data, status){
    console.log(data);
    if (data.status == "200") {
    map.removeLayer(layer);
    map.addLayer(layer);
    layer.redraw();
    location.reload(true);
    }
    else {
    let tempMsg = document.getElementById("mySearchMsg");
    tempMsg.style.visibility = "visible";
    tempMsg.value = data.msg;
    }
});
}


function search(){
    let tempBox = document.getElementById("searchBox");
    let temp = document.getElementById("mySearch");
    let tempButton = document.getElementById("mySearchButton");
    let tempMsg = document.getElementById("mySearchMsg");
    if (tempBox.style.visibility == "hidden") {
      tempBox.style.visibility = "visible";
      tempButton.style.visibility = "visible";
      temp.style.visibility = "visible";
      tempMsg.value = '';
      map.off('keypress', keyboardf);
    }
    else {
      tempBox.style.visibility = "hidden";
      tempButton.style.visibility = "hidden";
      temp.style.visibility = "hidden";
      tempMsg.style.visibility = "hidden";
      map.on('keypress', keyboardf);
    }
  }
/****************/

/*Classifications functions */

function custom(val) {
if (window.updates == 0) return;
var valid = window.validClassesCode.includes(val);
if (valid){
console.log(window.classesName[val]);
    if (window.classifiedTiles[window.selected]) {
        console.log('selected already', window.classifiedTiles[window.selected]);
    }
    else {
    window.classifiedTiles[window.selected] = {
        'class'  : val,
        'polygon': L.polygon(window.coords, {color: window.colors[val],  fillOpacity: 0.12}).bindTooltip(window.classesName[val]) };
    map.removeLayer(window.polygon);
    map.removeLayer(window.classifiedTiles[window.selected].polygon);
    map.addLayer(window.classifiedTiles[window.selected].polygon);
    $.get(window.server_url + "update", {user: window.username, gid:window.selected, class: window.classifiedTiles[window.selected].class });
    var props = { 'name': window.selected, 'class':  window.classesName[val] }
    info.update(props);
    };
};
}; //custom

function clear_selected(){
    if (window.updates == 0) return;
    if (window.classifiedTiles[window.selected]) {
        map.removeLayer(window.classifiedTiles[window.selected].polygon);
        delete window.classifiedTiles[window.selected];
        map.removeLayer(window.polygon);
        map.addLayer(window.polygon);
        $.get(window.server_url + "update", {user: window.username, gid:window.selected, class:-1});
        var props = { 'name': window.selected, 'class':  -1 };
        info.update(props);
    };

}; // clear_selected
  
/****************/