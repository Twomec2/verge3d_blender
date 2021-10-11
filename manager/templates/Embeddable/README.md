# Verge3D React.js Application Example

1) Create a React.js application via the Create React App utility:

    ```
    npx create-react-app react_v3d_app
    ```

2) Delete all files in the `react_v3d_app/src` directory.

3) Copy the content of the `manager/templates/Embeddable/public` Verge3D's
directory to `react_v3d_app/public`.

    Copy the content of the `manager/templates/Embeddable/src` Verge3D's
directory to `react_v3d_app/src`.

    Copy the engine file `build/v3d.js` to `react_v3d_app/public`.

4) Add the following script tag into `react_v3d_app/public/index.html`:

    ```html
    <script src="%PUBLIC_URL%/v3d.js"></script>
    ```

5) Create a `components` directory inside `react_v3d_app/src`. Then create a
file called `react_v3d_app/src/components/V3DApp.js` with the following content:

    ```js
    import React from 'react';

    import * as v3dAppAPI from '../v3dApp/app.js';
    import '../v3dApp/app.css';

    class V3DApp extends React.Component {

        #app = null;

        componentDidMount() {
            v3dAppAPI.createApp().then(app => {
                this.#app = app;
            });
        }

        componentWillUnmount() {
            if (this.#app !== null) {
                this.#app.dispose();
                this.#app = null;
            }
        }

        render() {
            return <div id={v3dAppAPI.CONTAINER_ID}>
                <div id="fullscreen_button" className="fullscreen-button fullscreen-open" title="Toggle fullscreen mode"></div>
            </div>;
        }
    }

    export default V3DApp;
    ```

6) Create a file `react_v3d_app/src/index.js` containing the following code:

    ```js
    import React from 'react';
    import ReactDOM from 'react-dom';

    import V3DApp from './components/V3DApp.js';

    ReactDOM.render(
        <V3DApp/>,
        document.getElementById('root')
    );
    ```

7) Run the development server by executing the following command in the
`react_v3d_app` directory:

    ```
    npm start
    ```

    By default the application now should be available at http://localhost:3000/.


# Verge3D Vue.js Application Example

1) Create a Vue.js application via the Vue CLI utility:

    ```
    npx @vue/cli create vue_v3d_app
    ```

2) Copy the content of the `manager/templates/Embeddable/public` Verge3D's
directory to `vue_v3d_app/public`.

    Copy the content of the `manager/templates/Embeddable/src` Verge3D's
directory to `vue_v3d_app/src`.

    Copy the engine file `build/v3d.js` to `vue_v3d_app/public`.

3) Add the following script tag into `vue_v3d_app/public/index.html`:

    ```html
    <script src="<%= BASE_URL %>v3d.js"></script>
    ```

4) Create a file `vue_v3d_app/src/components/V3DApp.vue` containing the following
code:

    ```js
    <template>
        <div :id="containerId">
            <div id="fullscreen_button" class="fullscreen-button fullscreen-open" title="Toggle fullscreen mode"></div>
        </div>
    </template>

    <script>
    import * as v3dAppAPI from '../v3dApp/app.js';

    export default {
        name: 'V3DApp',

        data() {
            return {
                containerId: v3dAppAPI.CONTAINER_ID,
            }
        },

        app: null,

        mounted() {
            v3dAppAPI.createApp().then(app => {
                this.$options.app = app;
            });
        },

        beforeDestroy() {
            if (this.$options.app) {
                this.$options.app.dispose();
                this.$options.app = null;
            }
        },
    }
    </script>

    <style>
    @import '../v3dApp/app.css';
    </style>
    ```

    NOTE: The `beforeDestroy()` hook is deprecated in Vue.js 3.0.0+, use `beforeUnmount()` instead.
    See: <a href="https://eslint.vuejs.org/rules/no-deprecated-destroyed-lifecycle.html">https://eslint.vuejs.org/rules/no-deprecated-destroyed-lifecycle.html</a>

5) Change `vue_v3d_app/src/App.vue` so it will look like this:

    ```js
    <template>
        <V3DApp></V3DApp>
    </template>

    <script>
    import V3DApp from './components/V3DApp.vue';

    export default {
        name: 'App',
        components: {
            V3DApp
        }
    }
    </script>
    ```

6) Run the development server by executing the following command in the
`vue_v3d_app` directory:

    ```
    npm run serve
    ```

    By default the application now should be available at http://localhost:8080/.
