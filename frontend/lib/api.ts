import axios from 'axios'
import { logger } from './logger'

const API_BASE_URL = process.env.BACKEND_URL || "http://localhost:8080/api"

export const api = axios.create({
	baseURL: API_BASE_URL,
	headers: {
		'Content-Type': 'application/json',
	},
})

// Request interceptor
api.interceptors.request.use(
	(config) => {
		logger.info(`API Request: ${config.method?.toUpperCase()} ${config.url}`, {
			method: config.method,
			url: config.url,
			data: config.data,
			params: config.params
		})
		return config
	},
	(error) => {
		logger.error('API Request Error', error)
		return Promise.reject(error)
	}
)

// Response interceptor
api.interceptors.response.use(
	(response) => {
		logger.info(`API Response: ${response.status} ${response.config.url}`, {
			status: response.status,
			url: response.config.url,
			data: response.data
		})
		return response
	},
	(error) => {
		logger.error('API Response Error', {
			status: error.response?.status,
			url: error.config?.url,
			message: error.message,
			data: error.response?.data
		})
		return Promise.reject(error)
	}
) 