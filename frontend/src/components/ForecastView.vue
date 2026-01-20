<template>
  <div class="forecast-view">
    <h2 class="mb-4">Forecast Analysis</h2>

    <!-- Filters -->
    <div class="card mb-4">
      <div class="card-body">
        <div class="row g-3">
          <div class="col-md-4">
            <label class="form-label">Category</label>
            <select class="form-select" v-model="selectedCategory" @change="loadData">
              <option value="">Select a category...</option>
              <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
            </select>
          </div>
          <div class="col-md-4">
            <label class="form-label">Model</label>
            <select class="form-select" v-model="selectedModel" @change="loadData">
              <option value="prophet">FB Prophet</option>
              <option value="sarimax">SARIMAX</option>
              <option value="holt_winters">Holt-Winters</option>
            </select>
          </div>
          <div class="col-md-4">
            <label class="form-label">&nbsp;</label>
            <button class="btn btn-primary w-100" @click="loadData" :disabled="!selectedCategory">
              <i class="bi bi-arrow-clockwise"></i> Load Forecast
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary"></div>
      <p class="mt-3">Loading data...</p>
    </div>

    <!-- No Data -->
    <div v-else-if="!selectedCategory" class="alert alert-info">
      <i class="bi bi-info-circle"></i> Please select a category to view forecasts.
    </div>

    <!-- Chart and Table -->
    <div v-else-if="historicalData.length > 0 || forecastData.length > 0">
      <!-- Chart -->
      <div class="card mb-4">
        <div class="card-body">
          <h5 class="card-title">
            {{ selectedCategory }} - {{ getModelName(selectedModel) }} Forecast
          </h5>
          <div class="chart-container">
            <canvas ref="chartCanvas"></canvas>
          </div>
        </div>
      </div>

      <!-- Forecast Table -->
      <div class="card">
        <div class="card-body">
          <h5 class="card-title">Forecast Data (Next 30 Days)</h5>
          <div class="table-responsive">
            <table class="table table-striped table-hover">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Forecast Value</th>
                  <th>Lower CI (95%)</th>
                  <th>Upper CI (95%)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in forecastData" :key="item.forecast_date">
                  <td>{{ item.forecast_date }}</td>
                  <td><strong>{{ formatNumber(item.forecast_value) }}</strong></td>
                  <td>{{ formatNumber(item.lower_bound) }}</td>
                  <td>{{ formatNumber(item.upper_bound) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="alert alert-warning">
      No data available for the selected category and model.
    </div>
  </div>
</template>

<script>
import { ref, onMounted, nextTick } from 'vue'
import axios from 'axios'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const API_URL = 'http://localhost:5000'

export default {
  name: 'ForecastView',
  setup() {
    const categories = ref([])
    const selectedCategory = ref('')
    const selectedModel = ref('prophet')
    const loading = ref(false)
    const historicalData = ref([])
    const forecastData = ref([])
    const chartCanvas = ref(null)
    let chartInstance = null

    const loadCategories = async () => {
      try {
        const response = await axios.get(`${API_URL}/invoice-data?limit=10000`)
        const uniqueCategories = [...new Set(response.data.data.map(item => item.category))]
        categories.value = uniqueCategories.sort()
      } catch (error) {
        console.error('Error loading categories:', error)
      }
    }

    const loadData = async () => {
      if (!selectedCategory.value) return

      loading.value = true
      try {
        // Load historical data for selected category
        const historicalResponse = await axios.get(`${API_URL}/invoice-data`, {
          params: { category: selectedCategory.value, limit: 10000 }
        })
        
        // Aggregate by date (sum sales per day)
        const aggregated = {}
        historicalResponse.data.data.forEach(item => {
          if (!aggregated[item.date]) {
            aggregated[item.date] = 0
          }
          aggregated[item.date] += parseFloat(item.sales)
        })

        historicalData.value = Object.keys(aggregated)
          .sort()
          .map(date => ({ date, sales: aggregated[date] }))

        // Load forecast data
        const forecastResponse = await axios.get(`${API_URL}/forecast-data`, {
          params: {
            category: selectedCategory.value,
            model_type: selectedModel.value,
            limit: 30
          }
        })
        
        forecastData.value = forecastResponse.data
          .sort((a, b) => new Date(a.forecast_date) - new Date(b.forecast_date))

        loading.value = false
        await nextTick()
        renderChart()
      } catch (error) {
        console.error('Error loading data:', error)
        loading.value = false
      }
    }

    const renderChart = () => {
      if (!chartCanvas.value) {
        console.error('Canvas element not found')
        return
      }

      // Destroy existing chart
      if (chartInstance) {
        chartInstance.destroy()
        chartInstance = null
      }

      const ctx = chartCanvas.value.getContext('2d')
      if (!ctx) {
        console.error('Cannot get 2D context')
        return
      }

      // Prepare data
      const historicalLabels = historicalData.value.map(d => d.date)
      const historicalValues = historicalData.value.map(d => d.sales)

      const forecastLabels = forecastData.value.map(d => d.forecast_date)
      const forecastValues = forecastData.value.map(d => parseFloat(d.forecast_value))
      const lowerBounds = forecastData.value.map(d => d.lower_bound !== null ? parseFloat(d.lower_bound) : parseFloat(d.forecast_value) * 0.9)
      const upperBounds = forecastData.value.map(d => d.upper_bound !== null ? parseFloat(d.upper_bound) : parseFloat(d.forecast_value) * 1.1)

      console.log('Rendering chart with:', {
        historicalPoints: historicalLabels.length,
        forecastPoints: forecastLabels.length
      })

      // Combine labels
      const allLabels = [...historicalLabels, ...forecastLabels]

      // Create datasets
      const datasets = [
        {
          label: 'Historical Sales',
          data: [...historicalValues, ...Array(forecastLabels.length).fill(null)],
          borderColor: '#0d6efd',
          backgroundColor: 'rgba(13, 110, 253, 0.1)',
          borderWidth: 2,
          pointRadius: 2,
          fill: false
        },
        {
          label: `${getModelName(selectedModel.value)} Forecast`,
          data: [...Array(historicalLabels.length).fill(null), ...forecastValues],
          borderColor: '#198754',
          backgroundColor: 'rgba(25, 135, 84, 0.1)',
          borderWidth: 2,
          borderDash: [5, 5],
          pointRadius: 3,
          fill: false
        },
        {
          label: 'Lower CI (95%)',
          data: [...Array(historicalLabels.length).fill(null), ...lowerBounds],
          borderColor: 'rgba(220, 53, 69, 0.3)',
          backgroundColor: 'rgba(220, 53, 69, 0.05)',
          borderWidth: 1,
          pointRadius: 0,
          fill: false
        },
        {
          label: 'Upper CI (95%)',
          data: [...Array(historicalLabels.length).fill(null), ...upperBounds],
          borderColor: 'rgba(220, 53, 69, 0.3)',
          backgroundColor: 'rgba(220, 53, 69, 0.15)',
          borderWidth: 1,
          pointRadius: 0,
          fill: '-1'
        }
      ]

      try {
        chartInstance = new Chart(ctx, {
          type: 'line',
          data: {
            labels: allLabels,
            datasets: datasets
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
              mode: 'index',
              intersect: false
            },
            plugins: {
              title: {
                display: true,
                text: `${selectedCategory.value} Sales Forecast - ${getModelName(selectedModel.value)}`
              },
              legend: {
                display: true,
                position: 'top'
              },
              tooltip: {
                callbacks: {
                  label: function(context) {
                    let label = context.dataset.label || ''
                    if (label) {
                      label += ': '
                    }
                    if (context.parsed.y !== null) {
                      label += formatNumber(context.parsed.y)
                    }
                    return label
                  }
                }
              }
            },
            scales: {
              y: {
                beginAtZero: false,
                title: {
                  display: true,
                  text: 'Sales'
                }
              },
              x: {
                title: {
                  display: true,
                  text: 'Date'
                }
              }
            }
          }
        })

        console.log('Chart created successfully:', chartInstance)
      } catch (error) {
        console.error('Error creating chart:', error)
      }
    }

    const getModelName = (model) => {
      const names = {
        prophet: 'FB Prophet',
        sarimax: 'SARIMAX',
        holt_winters: 'Holt-Winters'
      }
      return names[model] || model
    }

    const formatNumber = (value) => {
      if (value === null || value === undefined) return 'N/A'
      return parseFloat(value).toFixed(2)
    }

    onMounted(() => {
      loadCategories()
    })

    return {
      categories,
      selectedCategory,
      selectedModel,
      loading,
      historicalData,
      forecastData,
      chartCanvas,
      loadData,
      getModelName,
      formatNumber
    }
  }
}
</script>

<style scoped>
.chart-container {
  position: relative;
  height: 450px;
  width: 100%;
}

canvas {
  width: 100% !important;
  height: 100% !important;
}
</style>
