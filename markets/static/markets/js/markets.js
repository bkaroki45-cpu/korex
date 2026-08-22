(() => {
  let asset, interval = '240', tradingViewReady;
  const names = {BTC:'Bitcoin',ETH:'Ethereum',BNB:'BNB',SOL:'Solana',XRP:'XRP',DOGE:'Dogecoin',TRX:'TRON',ADA:'Cardano',AVAX:'Avalanche',LINK:'Chainlink'};
  const $ = id => document.getElementById(id);
  const money = value => Number.isFinite(Number(value)) ? '$' + Number(value).toLocaleString(undefined,{maximumFractionDigits:8}) : 'N/A';

  function loadTradingView() {
    if (window.TradingView) return Promise.resolve(window.TradingView);
    if (tradingViewReady) return tradingViewReady;
    tradingViewReady = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://s3.tradingview.com/tv.js';
      script.async = true;
      script.onload = () => window.TradingView ? resolve(window.TradingView) : reject(new Error('TradingView did not initialise.'));
      script.onerror = () => reject(new Error('TradingView could not be reached.'));
      document.head.appendChild(script);
    });
    return tradingViewReady;
  }

  function chart() {
    const container = $('tradingview-chart');
    if (!asset || !container) return;
    container.innerHTML = '<div class="chart-loading">Loading live chart...</div>';
    loadTradingView().then(() => {
      container.innerHTML = '';
      new window.TradingView.widget({container_id:'tradingview-chart',symbol:asset.tv,interval,timezone:'Africa/Nairobi',theme:'dark',style:'1',locale:'en',autosize:true,hide_side_toolbar:false,allow_symbol_change:false,withdateranges:true});
    }).catch(() => {
      container.innerHTML = '<div class="chart-loading chart-error">Live chart is unavailable. Check that this browser can reach TradingView, then refresh.</div>';
    });
  }

  function select(card) {
    asset = JSON.parse(card.dataset.asset);
    document.querySelectorAll('.market-card').forEach(item => item.classList.toggle('selected', item === card));
    $('selected-name').textContent = asset.name;
    $('selected-pair').textContent = asset.symbol + '/USDT';
    $('selected-price').textContent = money(asset.price);
    const change = $('selected-change');
    change.textContent = Number(asset.change).toFixed(2) + '% · 24h';
    change.className = Number(asset.change) >= 0 ? 'positive' : 'negative';
    [['fund-cap','cap'],['fund-volume','volume'],['fund-high','high'],['fund-low','low']].forEach(([id,key]) => $(id).textContent = money(asset[key]));
    $('fund-rank').textContent = asset.rank ? '#' + asset.rank : 'N/A';
    chart();
  }

  function bindCards() {
    document.querySelectorAll('.market-card').forEach(card => card.addEventListener('click', () => select(card)));
    const first = document.querySelector('.market-card');
    if (first) select(first);
  }

  function card(symbol, ticker, rank) {
    const data = {name:names[symbol],symbol,tv:'BINANCE:'+symbol+'USDT',price:ticker.lastPrice,change:ticker.priceChangePercent,cap:null,volume:ticker.quoteVolume,high:ticker.highPrice,low:ticker.lowPrice,rank};
    const item = document.createElement('button');
    item.type = 'button'; item.className = 'market-card'; item.dataset.asset = JSON.stringify(data); item.dataset.search = `${data.name} ${symbol} ${symbol}/USDT`;
    item.innerHTML = `<span class="market-name"><span class="coin-symbol">${symbol[0]}</span><span><strong>${data.name}</strong><small>${symbol}/USDT</small></span></span><span><strong>${money(data.price)}</strong><small class="${Number(data.change)>=0?'positive':'negative'}">${Number(data.change).toFixed(2)}% · 24h</small></span>`;
    return item;
  }

  async function fallback() {
    if (document.querySelector('.market-card')) return;
    const loading = $('market-loading');
    try {
      const response = await fetch('https://api.binance.com/api/v3/ticker/24hr');
      if (!response.ok) throw Error();
      const tickers = Object.fromEntries((await response.json()).map(item => [item.symbol,item]));
      let rank = 1;
      Object.keys(names).forEach(symbol => { if (tickers[symbol+'USDT']) $('market-list').appendChild(card(symbol,tickers[symbol+'USDT'],rank++)); });
      loading?.remove(); bindCards();
    } catch { if (loading) loading.textContent = 'Unable to connect to live market providers. Check this browser/server internet connection and retry.'; }
  }

  document.querySelectorAll('.timeframes button').forEach(button => button.addEventListener('click', () => { interval = button.dataset.interval; document.querySelectorAll('.timeframes button').forEach(item => item.classList.toggle('active', item === button)); chart(); }));
  $('market-search')?.addEventListener('input', event => { const query = event.target.value.toLowerCase(); document.querySelectorAll('.market-card').forEach(item => item.hidden = !item.dataset.search.toLowerCase().includes(query)); });
  bindCards(); fallback();
})();
