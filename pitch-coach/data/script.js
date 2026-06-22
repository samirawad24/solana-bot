/*
 * FEX (Final Expense) Sales Script — structured data
 * Source: Agent Training Manual provided by the user.
 *
 * Each section has:
 *   id        - stable key
 *   title     - display name
 *   purpose   - the "why": what this step accomplishes (used in Learn mode + coaching)
 *   script    - the spoken script. {placeholders} are things the agent fills in live.
 *   keyLines  - the load-bearing lines worth memorizing word-for-word
 *   blanks    - fill-in-the-blank prompts for Memorize mode
 *
 * This same content is mirrored server-side in netlify/functions/coach.js so the
 * AI grades against the real script. Keep the two in sync when you edit the pitch.
 */

(function (root, factory) {
  var data = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = data;
  if (root) root.FEX_SCRIPT = data;
})(typeof window !== "undefined" ? window : null, function () {
  return {
  agentNameDefault: "Nina",

  sections: [
    {
      id: "opening",
      title: "Opening",
      purpose:
        "Reconnect on the lead they submitted, verify their info, and frame yourself as the assigned underwriter so the call feels official and low-pressure. Keep it to ~5 minutes of perceived effort.",
      script:
        "Hey {client}, this is {agent}. I'm just getting back to you about the request you sent in to get information on the state regulated funeral & final expense coverage.\n\n" +
        "I see here that you put your date of birth down as {DOB} and your beneficiary as {beneficiary}. Is that correct?\n\n" +
        "Perfect, my job is very simple. I am just the underwriter assigned to go over this with you. It should take us about 5 minutes.\n\n" +
        "Go ahead and grab a pen and paper so I can give you my credentials. Let me know when you are ready.\n\n" +
        "(Give first and last name. Spell out your National Producer Number.)\n\n" +
        "With that number you can look me up on the Department of Insurance in your state and confirm that my license is active.",
      keyLines: [
        "I'm just getting back to you about the request you sent in to get information on the state regulated funeral & final expense coverage.",
        "My job is very simple. I am just the underwriter assigned to go over this with you. It should take us about 5 minutes.",
        "Grab a pen and paper so I can give you my credentials.",
        "With that number you can look me up on the Department of Insurance in your state and confirm that my license is active.",
      ],
      blanks: [
        {
          prompt: "I'm just getting back to you about the request you sent in to get information on the state regulated _______ & _______ coverage.",
          answers: ["funeral", "final expense"],
        },
        {
          prompt: "My job is very simple. I am just the _______ assigned to go over this with you.",
          answers: ["underwriter"],
        },
        {
          prompt: "Go ahead and grab a _______ and _______ so I can give you my credentials.",
          answers: ["pen", "paper"],
        },
      ],
    },
    {
      id: "find_why",
      title: "Find Why",
      purpose:
        "Surface the real reason they responded: protecting family from out-of-pocket costs. Get a verbal yes that anchors the rest of the call.",
      script:
        "Okay great, so {client}, normally when people are looking into funeral and final expense insurance, they are just looking to make sure that when something happens to them their family does not have to go out of pocket to cover those expenses.\n\n" +
        "Is that what you were looking for?",
      keyLines: [
        "Normally when people are looking into funeral and final expense insurance, they are just looking to make sure that when something happens to them their family does not have to go out of pocket to cover those expenses.",
        "Is that what you were looking for?",
      ],
      blanks: [
        {
          prompt: "They want to make sure that when something happens to them their family does not have to go _______ to cover those expenses.",
          answers: ["out of pocket"],
        },
      ],
    },
    {
      id: "important_questions",
      title: "Important Questions",
      purpose:
        "Qualify the situation and create urgency by getting them talking about who's responsible and what they have (or don't).",
      script:
        "Who is the person that's going to be responsible for your funeral and final arrangements when something happens to you?\n\n" +
        "Is this your first time looking for this type of coverage or have you been looking for a while?\n\n" +
        "Have you ever been declined for this type of coverage before?\n\n" +
        "Do you have existing coverage in place that would cover some of these expenses?",
      keyLines: [
        "Who is the person that's going to be responsible for your funeral and final arrangements when something happens to you?",
        "Is this your first time looking for this type of coverage or have you been looking for a while?",
        "Have you ever been declined for this type of coverage before?",
        "Do you have existing coverage in place that would cover some of these expenses?",
      ],
      blanks: [
        {
          prompt: "Who is the person that's going to be _______ for your funeral and final arrangements when something happens to you?",
          answers: ["responsible"],
        },
        {
          prompt: "Have you ever been _______ for this type of coverage before?",
          answers: ["declined"],
        },
      ],
    },
    {
      id: "coverage_branch",
      title: "Coverage Branch",
      purpose:
        "Take the right fork. If they have coverage, position this as topping up the gap. If not, find the emotional trigger that brought them here now.",
      script:
        "IF THEY HAVE COVERAGE:\n" +
        "Great! Most people I talk to have at least one other policy in place. I'm assuming you realized you need some more coverage to make sure all of those final expenses are taken care of for {beneficiary}.\n" +
        "Let me ask you a few additional questions on your current policy.\n" +
        "- How long have you had that current policy in place?\n" +
        "- How much coverage do you currently have?\n" +
        "- What is the monthly payment on your current coverage?\n\n" +
        "IF THEY DO NOT HAVE COVERAGE:\n" +
        "Have you had someone that recently passed that maybe prompted you to look into this, or was it you just realized it was time to get this plan in place because, let's face it, we are not getting any younger?\n" +
        "Makes sense.",
      keyLines: [
        "Most people I talk to have at least one other policy in place. I'm assuming you realized you need some more coverage to make sure all of those final expenses are taken care of.",
        "Have you had someone that recently passed that maybe prompted you to look into this, or was it you just realized it was time to get this plan in place because, let's face it, we are not getting any younger?",
      ],
      blanks: [
        {
          prompt: "Most people I talk to have at least one other policy in place. I'm assuming you realized you need some _______ coverage.",
          answers: ["more"],
        },
      ],
    },
    {
      id: "reiterate",
      title: "Reiterate",
      purpose:
        "Lock in agreement on the goal before transitioning to your credibility. A second yes on the same page builds momentum.",
      script:
        "Okay {client}, just so we're on the same page, you're looking for a plan that is going to be there in place for {beneficiary} so when something happens to you they won't have to go out of pocket to cover those funeral and final expenses, correct?",
      keyLines: [
        "Just so we're on the same page, you're looking for a plan that is going to be there in place for {beneficiary} so when something happens to you they won't have to go out of pocket to cover those funeral and final expenses, correct?",
      ],
      blanks: [
        {
          prompt: "Just so we're on the same page... so when something happens to you they won't have to go out of pocket to cover those funeral and final expenses, _______?",
          answers: ["correct"],
        },
      ],
    },
    {
      id: "credibility",
      title: "Credibility / Structure",
      purpose:
        "Establish that you're an independent broker who shops many carriers, and set expectations for the medical/finance questions that follow.",
      script:
        "So {client}, a little bit about me and what I do. I am a broker with the state of {state}.\n\n" +
        "I'm basically the Expedia for insurance. I work for about 30 different companies that offer this type of coverage.\n\n" +
        "Now what we will do is run through about two minutes of some basic medical and finance questions. Based on what you tell me I will look through the companies and see which ones might approve you, which ones might decline you, and which ones will offer you the best rate.\n\n" +
        "Does that make sense?",
      keyLines: [
        "I'm basically the Expedia for insurance. I work for about 30 different companies that offer this type of coverage.",
        "I will look through the companies and see which ones might approve you, which ones might decline you, and which ones will offer you the best rate.",
        "Does that make sense?",
      ],
      blanks: [
        {
          prompt: "I'm basically the _______ for insurance. I work for about _______ different companies that offer this type of coverage.",
          answers: ["Expedia", "30"],
        },
      ],
    },
    {
      id: "needs_analysis",
      title: "Needs Analysis",
      purpose:
        "Collect the basic health and lifestyle facts that determine carrier and rate. Stay conversational, not clinical.",
      script:
        "Do you smoke tobacco or nicotine products?\n\n" +
        "What is your approximate height and weight?\n\n" +
        "Are there any conditions that you are currently taking medication for?\n\n" +
        "Any major surgeries in the past 3 years?",
      keyLines: [
        "Do you smoke tobacco or nicotine products?",
        "What is your approximate height and weight?",
        "Are there any conditions that you are currently taking medication for?",
        "Any major surgeries in the past 3 years?",
      ],
      blanks: [
        {
          prompt: "Any major surgeries in the past _______ years?",
          answers: ["3", "three"],
        },
      ],
    },
    {
      id: "knockout",
      title: "Knockout Questions",
      purpose:
        "Screen for the conditions that move someone between level, graded, and guaranteed-issue plans. Ask them as a clean checklist.",
      script:
        "Have you ever had any of the following:\n" +
        "Heart attack, Stroke, Cancer, Stents, Diabetes, Neuropathy, High blood pressure, Lupus, Rheumatoid arthritis, Asthma or COPD, Anxiety or depression medication, Kidney disease, Liver disease?",
      keyLines: [
        "Have you ever had any of the following: heart attack, stroke, cancer, stents, diabetes, neuropathy, high blood pressure, lupus, rheumatoid arthritis, asthma or COPD, anxiety or depression medication, kidney disease, liver disease?",
      ],
      blanks: [
        {
          prompt: "Knockout list includes heart attack, stroke, _______, stents, diabetes, neuropathy...",
          answers: ["cancer"],
        },
      ],
    },
    {
      id: "final_expenses",
      title: "Funeral / Final Expenses",
      purpose:
        "Make the cost real. Anchor on today's burial and cremation prices so the coverage amount feels necessary, not optional.",
      script:
        "Are you planning on being cremated or buried?\n\n" +
        "Have you ever had to plan a funeral?\n\n" +
        "Do you want this plan to just cover funeral and final expenses, or would you like to leave a little bit more behind for {beneficiary}?\n\n" +
        "Do you know how much cremations or burials are costing today?\n" +
        "- Burial: $20,000 - $30,000\n" +
        "- Cremation: $10,000 - $15,000",
      keyLines: [
        "Do you want this plan to just cover funeral and final expenses, or would you like to leave a little bit more behind for {beneficiary}?",
        "Burial is running $20,000 to $30,000, and cremation is $10,000 to $15,000.",
      ],
      blanks: [
        {
          prompt: "Burial: $_______ - $_______.",
          answers: ["20,000", "30,000"],
        },
        {
          prompt: "Cremation: $_______ - $_______.",
          answers: ["10,000", "15,000"],
        },
      ],
    },
    {
      id: "find_carrier",
      title: "Find Carrier",
      purpose:
        "Place them on a brief hold and use your quoting tool (Life Center) to underwrite. The pause adds legitimacy.",
      script:
        "Alright {client}, let me go ahead and place you on a brief hold to see which company might approve you based on all of the questions I asked.\n\n" +
        "(Use Life Center to underwrite and quote the client.)",
      keyLines: [
        "Let me go ahead and place you on a brief hold to see which company might approve you based on all of the questions I asked.",
      ],
      blanks: [
        {
          prompt: "Let me place you on a brief _______ to see which company might approve you.",
          answers: ["hold"],
        },
      ],
    },
    {
      id: "explain_product",
      title: "Explain the Product",
      purpose:
        "Explain whole life in benefit language: never expires, locked-in price, builds cash value that can eventually pay the policy.",
      script:
        "The plan that came recommended for you is a whole life plan.\n\n" +
        "This plan is great because it will NEVER expire. Meaning you will never have to worry about securing coverage again because it will last your whole life.\n\n" +
        "Also, if you qualify, the price is locked in so your price will always stay the same.\n\n" +
        "The policy also accumulates cash value over time. Eventually there may be enough cash value where the policy can pay for itself and you can stop making payments while still keeping the coverage for life.",
      keyLines: [
        "The plan that came recommended for you is a whole life plan.",
        "It will NEVER expire... it will last your whole life.",
        "If you qualify, the price is locked in so your price will always stay the same.",
        "The policy also accumulates cash value over time.",
      ],
      blanks: [
        {
          prompt: "The plan that came recommended for you is a _______ plan.",
          answers: ["whole life"],
        },
        {
          prompt: "If you qualify, the price is _______ in so your price will always stay the same.",
          answers: ["locked"],
        },
        {
          prompt: "The policy also accumulates _______ over time.",
          answers: ["cash value"],
        },
      ],
    },
    {
      id: "brand_company",
      title: "Brand the Company",
      purpose:
        "Give the carrier authority: A-rated, financially strong, fast claims, and no medical exam needed.",
      script:
        "The company that came back recommended based on your age, your health and what you are looking for is {company}.\n\n" +
        "They are A rated, financially strong, and known for paying claims quickly.\n\n" +
        "They also allow us to apply for this coverage with NO medical exams - no urine samples, no nurses coming to your home, and no blood work.",
      keyLines: [
        "They are A rated, financially strong, and known for paying claims quickly.",
        "They allow us to apply for this coverage with NO medical exams - no urine samples, no nurses coming to your home, and no blood work.",
      ],
      blanks: [
        {
          prompt: "They are _______ rated, financially strong, and known for paying claims quickly.",
          answers: ["A"],
        },
        {
          prompt: "We can apply with NO medical exams - no urine samples, no nurses coming to your home, and no _______.",
          answers: ["blood work"],
        },
      ],
    },
    {
      id: "close",
      title: "The Close",
      purpose:
        "Present three coverage options (Bronze / Silver / Gold) and ask which amount they'd like to leave behind. Let them choose.",
      script:
        "(Have the client grab their pen and paper again. Write down three options.)\n\n" +
        "Bronze - lowest coverage and lowest premium\n" +
        "Silver - middle option\n" +
        "Gold - highest coverage option\n\n" +
        "Ask: Out of these three options, which amount would you like to leave behind for your beneficiary?",
      keyLines: [
        "Bronze, Silver, and Gold.",
        "Out of these three options, which amount would you like to leave behind for your beneficiary?",
      ],
      blanks: [
        {
          prompt: "The three options are _______, _______, and _______.",
          answers: ["Bronze", "Silver", "Gold"],
        },
        {
          prompt: "Out of these three options, which amount would you like to _______ for your beneficiary?",
          answers: ["leave behind"],
        },
      ],
    },
    {
      id: "application",
      title: "Application",
      purpose:
        "Set the expectation that the carrier must approve, then collect the information needed to submit.",
      script:
        "(Explain the insurance company must approve the policy.)\n\n" +
        "Collect:\n" +
        "- Full legal name\n" +
        "- Social Security number for prescription verification\n" +
        "- Banking information for the monthly premium",
      keyLines: [
        "The insurance company must approve the policy.",
        "I'll need your full legal name, Social Security number for prescription verification, and banking information for the monthly premium.",
      ],
      blanks: [
        {
          prompt: "Social Security number for _______ verification.",
          answers: ["prescription"],
        },
      ],
    },
    {
      id: "payment",
      title: "Payment Explanation",
      purpose:
        "Reassure that nothing is charged today and explain the simple draft timeline.",
      script:
        "If approved today nothing is charged today.\n\n" +
        "The first payment typically drafts within 3 to 5 business days and then continues monthly.",
      keyLines: [
        "If approved today nothing is charged today.",
        "The first payment typically drafts within 3 to 5 business days and then continues monthly.",
      ],
      blanks: [
        {
          prompt: "If approved today, _______ is charged today.",
          answers: ["nothing"],
        },
        {
          prompt: "The first payment typically drafts within _______ to _______ business days.",
          answers: ["3", "5"],
        },
      ],
    },
    {
      id: "post_close",
      title: "Post Close",
      purpose:
        "Confirm the key details, set delivery expectations, and remind them to inform the beneficiary. Leave them confident, not anxious.",
      script:
        "Confirm with the client:\n" +
        "- Coverage amount\n" +
        "- Monthly premium\n" +
        "- Payment date\n" +
        "- Policy number\n" +
        "- Your direct contact number\n\n" +
        "Let them know their policy packet will arrive within 7 to 10 days and they should inform their beneficiary.",
      keyLines: [
        "Confirm coverage amount, monthly premium, payment date, policy number, and your direct contact number.",
        "Your policy packet will arrive within 7 to 10 days - make sure you inform your beneficiary.",
      ],
      blanks: [
        {
          prompt: "Their policy packet will arrive within _______ to _______ days.",
          answers: ["7", "10"],
        },
      ],
    },
  ],

  // Common real-world FEX objections used in Objection Drills and injected into roleplay.
  objections: [
    { id: "afford", text: "Honestly, money's really tight right now. I don't think I can afford this.", tag: "Price" },
    { id: "think", text: "This sounds okay but I need some time to think about it.", tag: "Stall" },
    { id: "spouse", text: "I can't decide anything without talking to my husband/wife first.", tag: "Spouse" },
    { id: "mail", text: "Can you just mail me the information so I can look it over?", tag: "Brush-off" },
    { id: "have", text: "I already have life insurance through work, so I'm covered.", tag: "Existing coverage" },
    { id: "scam", text: "How do I even know this is real? This feels like a scam.", tag: "Trust" },
    { id: "callback", text: "Now's not a good time, can you call me back later?", tag: "Stall" },
    { id: "info", text: "Wait, how did you get my information?", tag: "Trust" },
    { id: "notinterested", text: "I'm really not interested, thanks.", tag: "Resistance" },
    { id: "rate", text: "That monthly price is higher than I expected. Why so much?", tag: "Price" },
    { id: "young", text: "I'm still pretty healthy, I feel like I can wait a few years on this.", tag: "Procrastination" },
    { id: "kids", text: "My kids said they'd just handle everything when the time comes.", tag: "Reframe" },
  ],

  // Scoring rubric (must mirror the server). Weights sum to 100.
  rubric: [
    { id: "opening", label: "Opening & credentials", weight: 15 },
    { id: "discovery", label: "Discovery & finding the why", weight: 15 },
    { id: "credibility", label: "Credibility & structure", weight: 10 },
    { id: "needs", label: "Needs analysis & knockout", weight: 10 },
    { id: "expenses", label: "Final-expense framing & cost anchoring", weight: 10 },
    { id: "product", label: "Product explanation & company branding", weight: 10 },
    { id: "objections", label: "Objection handling", weight: 15 },
    { id: "close", label: "The close & options", weight: 10 },
    { id: "compliance", label: "Compliance & tone", weight: 5 },
  ],
  };
});
