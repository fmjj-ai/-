import { createApp } from 'vue'
import store from './store'
import Antd from 'ant-design-vue'
import router from './router'
import App from './App.vue'
import 'ant-design-vue/dist/reset.css'
import './style.css'  /* 全局基础样式与 ant 组件柔化覆写 */

const app = createApp(App)

app.use(store)
app.use(router)
app.use(Antd)

app.mount('#app')
