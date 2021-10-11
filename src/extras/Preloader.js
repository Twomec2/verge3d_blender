import { Clock } from '../core/Clock.js';
import { Color } from '../math/Color.js';

import { LogoImage } from '../media.js';

function Preloader() {}

Object.assign(Preloader.prototype, {

    onUpdate: function(percentage) {},

    onFinish: function() {}

});


/**
 * parameters = {
 *  container: <HTMLElement|string>
 * }
 */
function SimplePreloader(parameters) {

    Preloader.call(this);

    for (let key in parameters) {
        const value = parameters[key];
        switch (key) {
        case 'container':
            if (value === undefined)
                this.container = document.body;
            else if (value instanceof HTMLElement)
                this.container = value;
            else
                this.container = document.getElementById(value);
            break;
        }
    }

    this.bar = document.createElement('div');
    this.bar.setAttribute('class', 'v3d-simple-preloader-bar');

    this.logo = document.createElement('div');
    this.logo.setAttribute('class', 'v3d-simple-preloader-logo');

    this.logoCont = document.createElement('div');
    this.logoCont.setAttribute('id', 'v3d_preloader_container');
    this.logoCont.setAttribute('class', 'v3d-simple-preloader-container');

    this.background = document.createElement('div');
    this.background.setAttribute('class', 'v3d-simple-preloader-background');

    this.background.appendChild(this.logoCont);

    this.logoCont.appendChild(this.logo);
    this.logoCont.appendChild(this.bar);

    this.container.appendChild(this.background);

    // assign default Data URL encoded logo image

    if (getComputedStyle(this.logo).backgroundImage == 'none')
        this.logo.setAttribute('style', 'background-image: url("' + LogoImage + '");');

    this.clock = new Clock();
}

SimplePreloader.prototype = Object.assign(Object.create(Preloader.prototype), {

    constructor: SimplePreloader,

    onUpdate: function(percentage) {
        percentage = Math.round(percentage);
        this.bar.style.width = percentage + '%';
    },

    onFinish: function() {
        this.container.removeChild(this.background);
    }

});

export { Preloader, SimplePreloader };
