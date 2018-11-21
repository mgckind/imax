import React from 'react';
import ReactDOM from 'react-dom';
import './index.css';
import App from './Header/App';
import Filters from './Filters/Filters'

ReactDOM.render(<App />, document.getElementById('header'));
ReactDOM.render(<Filters />, document.getElementById('filters'));