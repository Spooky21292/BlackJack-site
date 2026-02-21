const STORAGE_KEYS = {
  balance: 'bj_balance',
  clickIncome: 'bj_click_income'
};

const suits = ['♠', '♥', '♦', '♣'];
const ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'];

const state = {
  balance: loadNumber(STORAGE_KEYS.balance, 500),
  totalClickIncome: loadNumber(STORAGE_KEYS.clickIncome, 0),
  sessionClicks: 0,
  deck: [],
  playerHand: [],
  dealerHand: [],
  currentBet: 0,
  roundActive: false,
  dealerHidden: true,
  canDouble: false
};

const el = {
  tabs: document.querySelectorAll('.tab-btn'),
  panels: {
    blackjack: document.getElementById('tab-blackjack'),
    clicker: document.getElementById('tab-clicker'),
    rules: document.getElementById('tab-rules')
  },
  globalBalance: document.getElementById('globalBalance'),
  clickerBalance: document.getElementById('clickerBalance'),
  betInput: document.getElementById('betInput'),
  startRoundBtn: document.getElementById('startRoundBtn'),
  newRoundBtn: document.getElementById('newRoundBtn'),
  hitBtn: document.getElementById('hitBtn'),
  standBtn: document.getElementById('standBtn'),
  doubleBtn: document.getElementById('doubleBtn'),
  currentBet: document.getElementById('currentBet'),
  playerTotal: document.getElementById('playerTotal'),
  dealerTotal: document.getElementById('dealerTotal'),
  messageBox: document.getElementById('messageBox'),
  dealerCards: document.getElementById('dealerCards'),
  playerCards: document.getElementById('playerCards'),
  clickerBtn: document.getElementById('clickerBtn'),
  sessionClicks: document.getElementById('sessionClicks'),
  totalClickIncome: document.getElementById('totalClickIncome'),
  clickFxLayer: document.getElementById('clickFxLayer')
};

function loadNumber(key, fallback) {
  const raw = localStorage.getItem(key);
  const num = raw !== null ? Number(raw) : NaN;
  return Number.isFinite(num) ? num : fallback;
}

function saveProgress() {
  localStorage.setItem(STORAGE_KEYS.balance, String(state.balance));
  localStorage.setItem(STORAGE_KEYS.clickIncome, String(state.totalClickIncome));
}

function createDeck() {
  const deck = [];
  for (const suit of suits) {
    for (const rank of ranks) {
      deck.push({ suit, rank });
    }
  }
  return deck;
}

function shuffleDeck(deck) {
  for (let i = deck.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [deck[i], deck[j]] = [deck[j], deck[i]];
  }
}

function dealCard(hand) {
  if (!state.deck.length) {
    state.deck = createDeck();
    shuffleDeck(state.deck);
  }
  const card = state.deck.pop();
  hand.push(card);
  return card;
}

function rankValue(rank) {
  if (rank === 'A') return 11;
  if (['K', 'Q', 'J'].includes(rank)) return 10;
  return Number(rank);
}

function handValue(hand) {
  let total = 0;
  let aces = 0;

  for (const card of hand) {
    total += rankValue(card.rank);
    if (card.rank === 'A') aces += 1;
  }

  while (total > 21 && aces > 0) {
    total -= 10;
    aces -= 1;
  }

  return total;
}

function isBlackjack(hand) {
  return hand.length === 2 && handValue(hand) === 21;
}

function formatCard(card, hidden = false) {
  if (hidden) return '<div class="card back" aria-label="Скрытая карта"></div>';

  const red = card.suit === '♥' || card.suit === '♦';
  return `
    <div class="card ${red ? 'red' : ''}">
      <div>${card.rank}</div>
      <div class="suit">${card.suit}</div>
      <div style="align-self:end">${card.rank}</div>
    </div>
  `;
}

function setMessage(text) {
  el.messageBox.textContent = text;
}

function validateBet(rawValue) {
  const bet = Number(rawValue);
  if (!rawValue) return { ok: false, error: 'Введите ставку.' };
  if (!Number.isInteger(bet) || bet <= 0) return { ok: false, error: 'Ставка должна быть целым числом больше 0.' };
  if (bet > state.balance) return { ok: false, error: 'Ставка не может быть больше баланса.' };
  return { ok: true, bet };
}

function startRound() {
  if (state.roundActive) {
    setMessage('Раунд уже активен. Завершите текущую раздачу.');
    return;
  }

  const checked = validateBet(el.betInput.value.trim());
  if (!checked.ok) {
    setMessage(checked.error);
    return;
  }

  state.currentBet = checked.bet;
  state.playerHand = [];
  state.dealerHand = [];
  state.deck = createDeck();
  shuffleDeck(state.deck);
  state.roundActive = true;
  state.dealerHidden = true;
  state.canDouble = true;

  dealCard(state.playerHand);
  dealCard(state.dealerHand);
  dealCard(state.playerHand);
  dealCard(state.dealerHand);

  const playerBJ = isBlackjack(state.playerHand);
  const dealerBJ = isBlackjack(state.dealerHand);

  if (playerBJ || dealerBJ) {
    state.dealerHidden = false;
    settleRound(playerBJ, dealerBJ);
  } else {
    setMessage('Раунд начался. Ваш ход.');
  }

  renderUI();
}

function playerHit() {
  if (!state.roundActive) {
    setMessage('Сначала начните раунд.');
    return;
  }

  dealCard(state.playerHand);
  state.canDouble = false;

  if (handValue(state.playerHand) > 21) {
    state.dealerHidden = false;
    settleRound(false, false);
  } else {
    setMessage('Вы взяли карту. Выберите следующее действие.');
  }

  renderUI();
}

function playerStand() {
  if (!state.roundActive) {
    setMessage('Раунд не активен.');
    return;
  }

  state.dealerHidden = false;
  dealerPlay();
  settleRound(false, false);
  renderUI();
}

function playerDouble() {
  if (!state.roundActive) {
    setMessage('Раунд не активен.');
    return;
  }
  if (!state.canDouble || state.playerHand.length !== 2) {
    setMessage('Double доступен только на первых двух картах.');
    return;
  }
  if (state.balance < state.currentBet * 2) {
    setMessage('Недостаточно средств, чтобы удвоить ставку.');
    return;
  }

  state.currentBet *= 2;
  state.canDouble = false;
  dealCard(state.playerHand);

  if (handValue(state.playerHand) > 21) {
    state.dealerHidden = false;
    settleRound(false, false);
  } else {
    state.dealerHidden = false;
    dealerPlay();
    settleRound(false, false);
  }

  renderUI();
}

function dealerPlay() {
  while (handValue(state.dealerHand) < 17) {
    dealCard(state.dealerHand);
  }
}

function settleRound(forcePlayerBJ, forceDealerBJ) {
  const playerTotal = handValue(state.playerHand);
  const dealerTotal = handValue(state.dealerHand);
  const playerBJ = forcePlayerBJ || isBlackjack(state.playerHand);
  const dealerBJ = forceDealerBJ || isBlackjack(state.dealerHand);

  let delta = 0;
  let message = '';

  if (playerBJ && dealerBJ) {
    message = 'Push: у вас и у дилера BlackJack. Ставка возвращена.';
  } else if (playerBJ) {
    delta = state.currentBet * 1.5;
    message = `BlackJack! Победа +${delta} ₽ (выплата 3:2).`;
  } else if (dealerBJ) {
    delta = -state.currentBet;
    message = 'У дилера BlackJack. Вы проиграли ставку.';
  } else if (playerTotal > 21) {
    delta = -state.currentBet;
    message = 'Перебор! Вы проиграли ставку.';
  } else if (dealerTotal > 21) {
    delta = state.currentBet;
    message = `Дилер перебрал. Вы выиграли +${delta} ₽.`;
  } else if (playerTotal > dealerTotal) {
    delta = state.currentBet;
    message = `Вы выиграли +${delta} ₽.`;
  } else if (playerTotal < dealerTotal) {
    delta = -state.currentBet;
    message = 'Дилер сильнее. Вы проиграли ставку.';
  } else {
    message = 'Push: равные суммы. Ставка возвращена.';
  }

  state.balance += delta;
  state.roundActive = false;
  state.canDouble = false;
  saveProgress();
  setMessage(message);
}

function resetRoundState() {
  if (state.roundActive) {
    setMessage('Нельзя начать новую раздачу, пока текущая не завершена.');
    return;
  }
  state.playerHand = [];
  state.dealerHand = [];
  state.currentBet = 0;
  state.dealerHidden = true;
  el.betInput.value = '';
  setMessage('Готово к новой раздаче. Введите ставку.');
  renderUI();
}

function renderCards() {
  el.playerCards.innerHTML = state.playerHand.map((card) => formatCard(card)).join('');
  el.dealerCards.innerHTML = state.dealerHand
    .map((card, i) => formatCard(card, state.dealerHidden && i === 1 && state.roundActive))
    .join('');
}

function renderUI() {
  const playerTotal = handValue(state.playerHand);
  const dealerVisibleTotal = state.dealerHidden && state.roundActive
    ? rankValue(state.dealerHand[0]?.rank || '0')
    : handValue(state.dealerHand);

  el.globalBalance.textContent = String(state.balance);
  el.clickerBalance.textContent = String(state.balance);
  el.currentBet.textContent = String(state.currentBet);
  el.playerTotal.textContent = state.playerHand.length ? String(playerTotal) : '0';
  el.dealerTotal.textContent = state.dealerHand.length ? String(dealerVisibleTotal) : '0';
  el.sessionClicks.textContent = String(state.sessionClicks);
  el.totalClickIncome.textContent = String(state.totalClickIncome);

  el.betInput.disabled = state.roundActive;
  el.startRoundBtn.disabled = state.roundActive;
  el.newRoundBtn.disabled = state.roundActive;

  el.hitBtn.disabled = !state.roundActive;
  el.standBtn.disabled = !state.roundActive;
  el.doubleBtn.disabled = !state.roundActive || !state.canDouble || state.playerHand.length !== 2;

  renderCards();
}

function switchTab(tabName) {
  for (const btn of el.tabs) {
    btn.classList.toggle('active', btn.dataset.tab === tabName);
  }

  Object.entries(el.panels).forEach(([name, panel]) => {
    panel.classList.toggle('active', name === tabName);
  });
}

function addClickFx() {
  const fx = document.createElement('span');
  fx.className = 'float-plus';
  fx.textContent = '+1 ₽';
  fx.style.left = `${Math.random() * 80 + 10}%`;
  el.clickFxLayer.appendChild(fx);

  setTimeout(() => fx.remove(), 700);
}

function clickerGain() {
  state.balance += 1;
  state.totalClickIncome += 1;
  state.sessionClicks += 1;

  el.clickerBtn.classList.add('pulse');
  setTimeout(() => el.clickerBtn.classList.remove('pulse'), 100);

  addClickFx();
  saveProgress();
  renderUI();
}

function bindEvents() {
  el.tabs.forEach((btn) => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  el.startRoundBtn.addEventListener('click', startRound);
  el.newRoundBtn.addEventListener('click', resetRoundState);
  el.hitBtn.addEventListener('click', playerHit);
  el.standBtn.addEventListener('click', playerStand);
  el.doubleBtn.addEventListener('click', playerDouble);
  el.clickerBtn.addEventListener('click', clickerGain);
}

function init() {
  bindEvents();
  renderUI();
}

init();
