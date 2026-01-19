<template>
  <div class="glossary-view">
    <h2 class="mb-4">Glossary</h2>
    <p class="lead">Key terms and concepts in time series forecasting</p>

    <div class="accordion" id="glossaryAccordion">
      <div class="accordion-item" v-for="(item, index) in glossaryItems" :key="index">
        <h2 class="accordion-header">
          <button
            class="accordion-button collapsed"
            type="button"
            data-bs-toggle="collapse"
            :data-bs-target="'#collapse' + index"
          >
            <strong>{{ item.term }}</strong>
          </button>
        </h2>
        <div :id="'collapse' + index" class="accordion-collapse collapse" data-bs-parent="#glossaryAccordion">
          <div class="accordion-body">
            <p>{{ item.definition }}</p>
            <div v-if="item.example" class="alert alert-light">
              <strong>Example:</strong> {{ item.example }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'

export default {
  name: 'GlossaryView',
  setup() {
    const glossaryItems = ref([
      {
        term: 'FB Prophet',
        definition: 'Facebook Prophet is an open-source forecasting tool developed by Facebook (Meta). It is designed for forecasting time series data based on an additive model where non-linear trends are fit with yearly, weekly, and daily seasonality, plus holiday effects. Prophet is robust to missing data and shifts in the trend, and typically handles outliers well.',
        example: 'Prophet is particularly useful for business forecasting tasks where historical patterns repeat annually or weekly, such as retail sales or website traffic.'
      },
      {
        term: 'SARIMAX',
        definition: 'Seasonal AutoRegressive Integrated Moving Average with eXogenous factors (SARIMAX) is a statistical model used for time series forecasting. It extends the ARIMA model by incorporating seasonal components and external variables. SARIMAX captures both non-seasonal and seasonal patterns in the data and can account for external influences on the time series.',
        example: 'SARIMAX can be used to forecast monthly sales where there are yearly seasonal patterns (e.g., higher sales in December) and external factors like promotional campaigns affect sales.'
      },
      {
        term: 'Holt-Winters',
        definition: 'The Holt-Winters method, also known as Triple Exponential Smoothing, is a time series forecasting technique that accounts for three components: level (average value), trend (increasing or decreasing pattern), and seasonality (repeating patterns). It uses exponential smoothing to give more weight to recent observations while still considering historical data.',
        example: 'Holt-Winters is effective for forecasting demand for products that have both seasonal patterns and an underlying growth trend, such as ice cream sales (seasonal) with increasing popularity (trend).'
      },
      {
        term: 'Confidence Interval (CI)',
        definition: 'A Confidence Interval is a range of values that is likely to contain the true value of a parameter with a certain level of confidence, typically 95%. In forecasting, CI provides upper and lower bounds around the predicted value, indicating the uncertainty of the forecast. A wider interval suggests higher uncertainty.',
        example: 'A forecast of 1000 units with a 95% CI of [900, 1100] means we are 95% confident the actual value will fall between 900 and 1100 units.'
      },
      {
        term: 'Time Series',
        definition: 'A time series is a sequence of data points indexed in time order. Time series data is collected at successive time intervals, such as daily sales, monthly revenue, or yearly temperature. The goal of time series analysis is to understand underlying patterns (trend, seasonality, cyclicality) and forecast future values.',
        example: 'Daily stock prices, monthly unemployment rates, and hourly website traffic are all examples of time series data.'
      },
      {
        term: 'Imputation',
        definition: 'Imputation is the process of replacing missing or null values in a dataset with substituted values. Common imputation methods include forward-fill (using the previous value), backward-fill (using the next value), mean/median imputation, or more sophisticated statistical methods. Proper imputation is crucial for maintaining data quality and avoiding biased forecasts.',
        example: 'If sales data for January 15th is missing, forward-fill imputation would use the sales value from January 14th to fill the gap.'
      },
      {
        term: 'Batch Number',
        definition: 'A Batch Number is a unique identifier assigned to each file upload session. It allows tracking of when data was uploaded, which file it came from, and the processing status. Batch numbers enable traceability and help identify which data version is being used in forecasts.',
        example: 'Batch number "sales_2026_01_19_abc123" indicates a sales file uploaded on January 19, 2026, with a unique identifier abc123.'
      },
      {
        term: 'ETL (Extract, Transform, Load)',
        definition: 'ETL is a data integration process that involves extracting data from source systems, transforming it to fit operational needs (cleaning, validation, aggregation), and loading it into a target database or data warehouse. In this platform, ETL validates CSV uploads, cleans missing values, and loads processed data into the database.',
        example: 'When you upload a CSV file, the ETL process extracts the data, validates column formats, imputes missing sales values, and loads the cleaned data into the invoice_data table.'
      },
      {
        term: 'Seasonality',
        definition: 'Seasonality refers to periodic fluctuations in time series data that occur at regular intervals due to seasonal factors. Seasonal patterns can be daily, weekly, monthly, or yearly. Identifying and modeling seasonality is essential for accurate forecasting.',
        example: 'Retail sales typically show yearly seasonality with peaks during holiday seasons (November-December) and troughs in post-holiday months (January-February).'
      },
      {
        term: 'Trend',
        definition: 'A trend is the long-term movement or direction in time series data, showing whether values are generally increasing, decreasing, or remaining stable over time. Trends can be linear (constant rate of change) or non-linear (changing rate of change).',
        example: 'A company experiencing steady growth might show an upward trend in monthly revenue, increasing by approximately 5% each month.'
      },
      {
        term: 'Upsert',
        definition: 'Upsert is a database operation that combines INSERT and UPDATE. If a record with the specified primary key does not exist, it inserts a new record. If it already exists, it updates the existing record. This ensures data integrity and prevents duplicates while allowing for data corrections.',
        example: 'When uploading corrected sales data for a date-product-category combination that already exists, upsert updates the existing record instead of creating a duplicate.'
      },
      {
        term: 'SHA256 Hash',
        definition: 'SHA256 (Secure Hash Algorithm 256-bit) is a cryptographic hash function that generates a unique fixed-size 256-bit hash value from input data. Even a tiny change in the input produces a completely different hash. In this platform, SHA256 is used to detect duplicate file uploads by comparing file content hashes.',
        example: 'Two files with identical content will always produce the same SHA256 hash, allowing the system to reject duplicate uploads even if filenames differ.'
      },
      {
        term: 'Forecast Horizon',
        definition: 'The forecast horizon is the length of time into the future for which predictions are made. It defines how many time periods ahead the model will forecast. Longer horizons generally have higher uncertainty.',
        example: 'A 30-day forecast horizon means the model predicts sales for the next 30 days from the last observed data point.'
      },
      {
        term: 'Category-Wise Forecasting',
        definition: 'Category-wise forecasting generates predictions at the product category level rather than individual product level. This aggregation can improve forecast accuracy by reducing noise from individual product variations and capturing overall category trends.',
        example: 'Instead of forecasting sales for each individual electronic product, category-wise forecasting predicts total sales for the entire Electronics category.'
      },
      {
        term: 'Composite Primary Key',
        definition: 'A composite primary key is a primary key that consists of multiple columns. Together, these columns uniquely identify each record in a database table. Composite keys are useful when a single column cannot guarantee uniqueness.',
        example: 'In the invoice_data table, the combination of (date, product_id, category) forms a composite primary key, ensuring no duplicate records for the same product on the same date.'
      }
    ])

    return {
      glossaryItems
    }
  }
}
</script>

<style scoped>
.accordion-button {
  font-size: 1.1rem;
}

.accordion-body {
  font-size: 1rem;
  line-height: 1.6;
}
</style>
