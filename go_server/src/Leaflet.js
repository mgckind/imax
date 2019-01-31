import React, { Component } from 'react';
import { render } from 'react-dom';
import { Map, TileLayer } from 'react-leaflet';
import "leaflet/dist/leaflet.css";

export class Leaflet extends Component {
    render() {
        return (
            <Map LeafletMap center={[0, -256]} style={{height: "512px", width: "512px"}} zoom={0}>
                <TileLayer
                    url="http://localhost:8080/map?x={x}&y={y}&z={z}"
                    maxZoom="5"
                />
            </Map>
        );
    }
}

render(
    <Leaflet />,
    document.getElementById('mount')
);
