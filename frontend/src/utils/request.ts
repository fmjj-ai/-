import axios from 'axios'
import type { AxiosError, AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { message } from 'ant-design-vue'

export const getErrorDetail = (error: any, fallback: string) => error?.response?.data?.detail || fallback

const request: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request Interceptor
request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // You can add token here if authentication is needed
    // const token = localStorage.getItem('token')
    // if (token) {
    //   config.headers['Authorization'] = `Bearer ${token}`
    // }
    return config
  },
  (error: AxiosError) => Promise.reject(error)
)

// Response Interceptor
request.interceptors.response.use(
  (response: AxiosResponse) => {
    const res = response.data

    // Customize based on backend response structure
    // If you have a standard response wrapper like { code, data, message }
    // if (res.code !== 200 && res.code !== 0) {
    //   message.error(res.message || 'Error')
    //   return Promise.reject(new Error(res.message || 'Error'))
    // }

    return res as any
  },
  (error: AxiosError) => {
    if (error.response) {
      switch (error.response.status) {
        case 401:
          message.error('未授权，请重新登录')
          // Redirect to login if necessary
          break
        case 403:
          message.error('拒绝访问')
          break
        case 404:
          message.error('请求地址出错')
          break
        case 500:
          message.error('服务器内部错误')
          break
        default:
          message.error(`网络错误: ${error.message}`)
      }
    } else {
      message.error('网络连接异常')
    }
    return Promise.reject(error)
  }
)

export default request
