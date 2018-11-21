import React, { Component } from 'react';
import '../App.css';
import Leaflet from '../Leaflet.js';

import { library } from '@fortawesome/fontawesome-svg-core'
import { faSearch, faFilter, faChartArea } from '@fortawesome/free-solid-svg-icons'

library.add(faSearch, faFilter, faChartArea);

class App extends Component {
  render() {
    return (
      <div className="App">
        <div className="Header">
          <p> ***</p>
          <p> NCSA Images </p>
        </div>
      </div>
    );
  }
}

export default App;
