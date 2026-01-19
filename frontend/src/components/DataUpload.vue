<template>
  <div class="data-upload">
    <h2 class="mb-4">Data Upload</h2>

    <!-- Upload Section -->
    <div class="card mb-4">
      <div class="card-body">
        <h5 class="card-title">Upload CSV File</h5>
        
        <!-- Drag & Drop Area -->
        <div 
          class="drop-zone" 
          :class="{ 'drag-over': isDragging }"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @drop.prevent="handleDrop"
          @click="$refs.fileInput.click()"
        >
          <i class="bi bi-cloud-arrow-up" style="font-size: 3rem; color: #0d6efd;"></i>
          <p class="mt-3 mb-2">Drag and drop your CSV file here</p>
          <p class="text-muted">or click to browse</p>
          <input 
            ref="fileInput" 
            type="file" 
            accept=".csv" 
            @change="handleFileSelect" 
            style="display: none;"
          />
        </div>

        <div v-if="selectedFile" class="alert alert-info mt-3">
          <i class="bi bi-file-earmark-text"></i> Selected: <strong>{{ selectedFile.name }}</strong> ({{ formatSize(selectedFile.size) }})
          <button class="btn btn-sm btn-outline-secondary ms-3" @click="clearFile">Clear</button>
        </div>

        <button 
          class="btn btn-primary mt-3" 
          @click="uploadFile" 
          :disabled="!selectedFile || uploading"
        >
          <span v-if="uploading" class="spinner-border spinner-border-sm me-2"></span>
          {{ uploading ? 'Uploading...' : 'Upload' }}
        </button>

        <!-- Upload Status Messages -->
        <div v-if="uploadMessage" class="alert mt-3" :class="uploadMessageClass">
          {{ uploadMessage }}
          <a v-if="duplicateBatch" href="#" @click.prevent="viewBatch(duplicateBatch)" class="alert-link ms-2">
            View Batch: {{ duplicateBatch }}
          </a>
        </div>
      </div>
    </div>

    <!-- Upload History Table -->
    <div class="card">
      <div class="card-body">
        <h5 class="card-title">Upload History</h5>
        <button class="btn btn-sm btn-outline-primary mb-3" @click="fetchMetadata">
          <i class="bi bi-arrow-clockwise"></i> Refresh
        </button>
        <div v-if="hasProcessingItems" class="badge bg-info ms-2">
          <i class="bi bi-hourglass-split"></i> Auto-refreshing...
        </div>

        <div v-if="loading" class="text-center py-4">
          <div class="spinner-border text-primary"></div>
        </div>

        <div v-else-if="metadata.length === 0" class="alert alert-info">
          No uploads yet. Upload your first CSV file above!
        </div>

        <div v-else class="table-responsive">
          <table class="table table-hover">
            <thead>
              <tr>
                <th>Batch Number</th>
                <th>Filename</th>
                <th>Uploaded At</th>
                <th>Total Rows</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in metadata" :key="item.batch_num">
                <td><code>{{ item.batch_num }}</code></td>
                <td>{{ item.original_filename }}</td>
                <td>{{ formatDate(item.uploaded_at) }}</td>
                <td>{{ item.num_total_rows || 'N/A' }}</td>
                <td>
                  <span class="badge" :class="getStatusClass(item.status)">
                    <span v-if="item.status === 'processing'" class="spinner-border spinner-border-sm me-1"></span>
                    {{ item.status }}
                  </span>
                </td>
                <td>
                  <button class="btn btn-sm btn-outline-info" @click="viewDetails(item)">
                    <i class="bi bi-eye"></i> View
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Details Modal -->
    <div class="modal fade" id="detailsModal" tabindex="-1">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Upload Details</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body" v-if="selectedItem">
            <table class="table table-bordered">
              <tbody>
                <tr>
                  <th width="30%">Batch Number</th>
                  <td><code>{{ selectedItem.batch_num }}</code></td>
                </tr>
                <tr>
                  <th>Original Filename</th>
                  <td>{{ selectedItem.original_filename }}</td>
                </tr>
                <tr>
                  <th>Stored Filename</th>
                  <td><code>{{ selectedItem.stored_filename }}</code></td>
                </tr>
                <tr>
                  <th>File Hash (SHA256)</th>
                  <td><code class="small">{{ selectedItem.file_hash }}</code></td>
                </tr>
                <tr>
                  <th>Uploaded At</th>
                  <td>{{ formatDate(selectedItem.uploaded_at) }}</td>
                </tr>
                <tr>
                  <th>Total Rows</th>
                  <td>{{ selectedItem.num_total_rows }}</td>
                </tr>
                <tr>
                  <th>Missing Rows</th>
                  <td>{{ selectedItem.num_missing_rows }}</td>
                </tr>
                <tr>
                  <th>Imputed Rows</th>
                  <td>{{ selectedItem.num_imputed_rows }}</td>
                </tr>
                <tr>
                  <th>Inserted Rows</th>
                  <td>{{ selectedItem.num_inserted_rows }}</td>
                </tr>
                <tr>
                  <th>Updated Rows</th>
                  <td>{{ selectedItem.num_updated_rows }}</td>
                </tr>
                <tr>
                  <th>Status</th>
                  <td>
                    <span class="badge" :class="getStatusClass(selectedItem.status)">
                      {{ selectedItem.status }}
                    </span>
                  </td>
                </tr>
                <tr v-if="selectedItem.error_log">
                  <th>Error Log</th>
                  <td><pre class="small mb-0">{{ selectedItem.error_log }}</pre></td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import axios from 'axios'
import { Modal } from 'bootstrap'

const API_URL = 'http://localhost:5000'

export default {
  name: 'DataUpload',
  setup() {
    const selectedFile = ref(null)
    const isDragging = ref(false)
    const uploading = ref(false)
    const uploadMessage = ref('')
    const uploadMessageClass = ref('')
    const duplicateBatch = ref(null)
    const metadata = ref([])
    const loading = ref(false)
    const selectedItem = ref(null)
    let refreshInterval = null

    const hasProcessingItems = computed(() => {
      return metadata.value.some(item => 
        item.status === 'uploaded' || item.status === 'processing'
      )
    })

    const handleDrop = (e) => {
      isDragging.value = false
      const files = e.dataTransfer.files
      if (files.length > 0) {
        selectedFile.value = files[0]
      }
    }

    const handleFileSelect = (e) => {
      const files = e.target.files
      if (files.length > 0) {
        selectedFile.value = files[0]
      }
    }

    const clearFile = () => {
      selectedFile.value = null
      uploadMessage.value = ''
      duplicateBatch.value = null
    }

    const uploadFile = async () => {
      if (!selectedFile.value) return

      uploading.value = true
      uploadMessage.value = ''
      duplicateBatch.value = null

      const formData = new FormData()
      formData.append('file', selectedFile.value)

      try {
        const response = await axios.post(`${API_URL}/upload`, formData)
        uploadMessage.value = `Success! Batch: ${response.data.batch_num}`
        uploadMessageClass.value = 'alert-success'
        selectedFile.value = null
        fetchMetadata()
        startAutoRefresh()
      } catch (error) {
        if (error.response?.status === 409) {
          uploadMessage.value = 'Duplicate file detected!'
          duplicateBatch.value = error.response.data.batch_num
          uploadMessageClass.value = 'alert-warning'
        } else {
          uploadMessage.value = `Error: ${error.response?.data?.error || error.message}`
          uploadMessageClass.value = 'alert-danger'
        }
      } finally {
        uploading.value = false
      }
    }

    const fetchMetadata = async () => {
      loading.value = true
      try {
        const response = await axios.get(`${API_URL}/metadata`)
        metadata.value = response.data
        
        // Stop auto-refresh if no items are processing
        if (!hasProcessingItems.value && refreshInterval) {
          clearInterval(refreshInterval)
          refreshInterval = null
        }
      } catch (error) {
        console.error('Error fetching metadata:', error)
      } finally {
        loading.value = false
      }
    }

    const startAutoRefresh = () => {
      if (!refreshInterval) {
        refreshInterval = setInterval(() => {
          fetchMetadata()
        }, 3000) // Refresh every 3 seconds
      }
    }

    const viewDetails = (item) => {
      selectedItem.value = item
      const modal = new Modal(document.getElementById('detailsModal'))
      modal.show()
    }

    const viewBatch = (batchNum) => {
      const item = metadata.value.find(m => m.batch_num === batchNum)
      if (item) {
        viewDetails(item)
      }
    }

    const formatDate = (dateStr) => {
      if (!dateStr) return 'N/A'
      return new Date(dateStr).toLocaleString()
    }

    const formatSize = (bytes) => {
      if (bytes < 1024) return bytes + ' B'
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    }

    const getStatusClass = (status) => {
      const classes = {
        uploaded: 'bg-secondary',
        processing: 'bg-info',
        completed: 'bg-success',
        failed: 'bg-danger'
      }
      return classes[status] || 'bg-secondary'
    }

    onMounted(() => {
      fetchMetadata()
    })

    onUnmounted(() => {
      if (refreshInterval) {
        clearInterval(refreshInterval)
      }
    })

    return {
      selectedFile,
      isDragging,
      uploading,
      uploadMessage,
      uploadMessageClass,
      duplicateBatch,
      metadata,
      loading,
      selectedItem,
      hasProcessingItems,
      handleDrop,
      handleFileSelect,
      clearFile,
      uploadFile,
      fetchMetadata,
      viewDetails,
      viewBatch,
      formatDate,
      formatSize,
      getStatusClass
    }
  }
}
</script>

<style scoped>
.drop-zone {
  border: 2px dashed #0d6efd;
  border-radius: 8px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  background-color: #f8f9fa;
}

.drop-zone:hover {
  background-color: #e7f1ff;
  border-color: #0a58ca;
}

.drop-zone.drag-over {
  background-color: #cfe2ff;
  border-color: #0a58ca;
  transform: scale(1.02);
}
</style>
