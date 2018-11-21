import React, { Component } from 'react';
import '../App.css';
import Leaflet from '../Leaflet.js';

import { library } from '@fortawesome/fontawesome-svg-core'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faSearch, faFilter, faChartArea } from '@fortawesome/free-solid-svg-icons'

library.add(faSearch, faFilter, faChartArea);

class Filters extends Component {
    render() {
        return (
            <div className="Filters">
                <button type="button">
                    <div id="search-button">
                        <FontAwesomeIcon icon="search" />
                        <p>Search</p>
                    </div>
                </button>
                <button type="button">
                    <div id="filter-button">
                        <FontAwesomeIcon icon="filter" />
                        <p>Filter</p>
                    </div>
                </button>
                <button type="button">
                    <div id="view-button">
                        <FontAwesomeIcon icon="chart-area" />
                        <p>Filter</p>
                    </div>
                </button>
            </div>
        );
    }
}

export default Filters;
