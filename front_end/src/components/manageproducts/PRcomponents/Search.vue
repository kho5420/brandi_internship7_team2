<template>
  <a-select
    mode="multiple"
    label-in-value
    :value="value"
    placeholder="Select users"
    style="width: 100%"
    :filter-option="false"
    :not-found-content="fetching ? undefined : null"
    @search="fetchUser"
    @change="handleChange"
  >
    <a-spin v-if="fetching" slot="notFoundContent" size="small" />
    <a-select-option v-for="d in data" :key="d.value">
      {{ d.text }}
    </a-select-option>
  </a-select>
</template>
<script>
import debounce from 'lodash/debounce';

export default {
  name: 'Search',
  data() {
    this.lastFetchId = 0;
    this.fetchUser = debounce(this.fetchUser, 800);
    return {
      data: [],
      value: [],
      fetching: false
    };
  },
  methods: {
    fetchUser(value) {
      console.log('fetching user', value);
      this.lastFetchId += 1;
      const fetchId = this.lastFetchId;
      this.data = [];
      this.fetching = true;
      fetch('https://randomuser.me/api/?results=5')
        .then((response) => response.json())
        .then((body) => {
          if (fetchId !== this.lastFetchId) {
            // for fetch callback order
            return;
          }
          const data = body.results.map((user) => ({
            text: `${user.name.first} ${user.name.last}`,
            value: user.login.username
          }));
          this.data = data;
          this.fetching = false;
        });
    },
    handleChange(value) {
      Object.assign(this, {
        value,
        data: [],
        fetching: false
      });
    }
  }
};
</script>

<a-icon type="search" />
