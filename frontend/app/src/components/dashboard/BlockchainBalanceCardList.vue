<template>
  <v-list-item
    v-if="amount !== zero"
    :id="`${name}_box`"
    :ripple="false"
    to="/blockchain-accounts"
    class="blockchain-balance-box__item"
  >
    <v-list-item-avatar tile class="blockchain-balance-box__icon">
      <crypto-icon
        width="24px"
        :symbol="blockchainBalanceIcons[name]"
      ></crypto-icon>
    </v-list-item-avatar>
    <v-list-item-content>
      <v-list-item-title class="d-flex justify-space-between">
        <span>
          {{ name | capitalize }}
        </span>
        <span class="text-end">
          <amount-display
            show-currency="symbol"
            fiat-currency="USD"
            :value="amount"
          ></amount-display>
        </span>
      </v-list-item-title>
    </v-list-item-content>
  </v-list-item>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Prop, Vue } from 'vue-property-decorator';
import CryptoIcon from '@/components/CryptoIcon.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { Zero } from '@/utils/bignumbers';

@Component({
  components: { AmountDisplay, CryptoIcon }
})
export default class BlockchainBalanceCardList extends Vue {
  @Prop({ required: true })
  name!: string;
  @Prop({ required: true })
  amount!: BigNumber;

  zero = Zero;

  blockchainBalanceIcons = {
    bitcoin: 'BTC',
    ethereum: 'ETH'
  };
}
</script>
<style scoped lang="scss">
.blockchain-balance-box {
  &__icon {
    filter: grayscale(100%);
  }
  &__item:hover &__icon {
    filter: grayscale(0);
  }

  &__icon--inverted {
    margin-left: 8px;
    width: 45px;
    filter: grayscale(100%) invert(100%);
  }
}
</style>
