import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  timeout: 60000
})

request.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(error)
)

export default request
