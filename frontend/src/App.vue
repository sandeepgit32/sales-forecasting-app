<template>
  <div id="app">
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
      <div class="container-fluid">
        <a class="navbar-brand" href="#">
          <i class="bi bi-graph-up-arrow"></i> Time Series Forecasting
        </a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
          <ul class="navbar-nav">
            <li class="nav-item">
              <a class="nav-link" :class="{ active: activeTab === 'upload' }" @click="activeTab = 'upload'" href="#">
                <i class="bi bi-cloud-upload"></i> Data Upload
              </a>
            </li>
            <li class="nav-item">
              <a class="nav-link" :class="{ active: activeTab === 'forecast' }" @click="activeTab = 'forecast'" href="#">
                <i class="bi bi-graph-up"></i> Forecast
              </a>
            </li>
            <li class="nav-item">
              <a class="nav-link" :class="{ active: activeTab === 'glossary' }" @click="activeTab = 'glossary'" href="#">
                <i class="bi bi-book"></i> Glossary
              </a>
            </li>
          </ul>
        </div>
      </div>
    </nav>

    <div class="container-fluid mt-4">
      <DataUpload v-if="activeTab === 'upload'" />
      <ForecastView v-if="activeTab === 'forecast'" />
      <GlossaryView v-if="activeTab === 'glossary'" />
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import DataUpload from './components/DataUpload.vue'
import ForecastView from './components/ForecastView.vue'
import GlossaryView from './components/GlossaryView.vue'

export default {
  name: 'App',
  components: {
    DataUpload,
    ForecastView,
    GlossaryView
  },
  setup() {
    const activeTab = ref('upload')
    return { activeTab }
  }
}
</script>

<style>
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.nav-link {
  cursor: pointer;
}
</style>
