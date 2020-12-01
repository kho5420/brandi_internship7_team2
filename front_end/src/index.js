import { createApp } from 'vue';
import axios from 'axios';
import App from './App.vue';
import router from './router.js';
import './styles/common.scss';
import './styles/reset.scss';

const app = createApp(App);
app.config.productionTip = false;
axios.defaults.baseURL = 'http://localhost:9000/';
axios.defaults.withCredentials = true;
app.use(router);
app.mount('#app');
