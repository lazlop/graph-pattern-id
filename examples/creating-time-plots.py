#%%
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

# # Set the Seaborn style
# sns.set_theme(style="white")

df = pd.read_csv('query-time.csv')

xticks = [round(n/1000,1) for n in df['model_length']]
plt.figure(figsize=(6,2))
plt.ylabel('Query Time (seconds)')
plt.plot(xticks,df['not_condensed_t'], label='Brick', color = 'tab:blue')
plt.plot(xticks,df['condensed_t'], label='Brick with b-schema', color = 'tab:green')
# plt.xlabel('Size of Model (1000s of Triples)')
# plt.xticks(xticks[::2])
# plt.xticks(model_length, [f'{1+i} [{x}]' for i,x in enumerate(model_length)])
# plt.legend()
# plt.tight_layout()
# plt.show()
# plt.savefig('query-time.png')

df = pd.read_csv('query-time-s223.csv')

xticks = [round(n/1000,1) for n in df['model_length']]
# plt.figure(figsize=(6,2.5))
plt.ylabel('Query Time (seconds)')
plt.plot(xticks,df['not_condensed_t'], label='S223', linestyle='--', color = 'tab:red')
plt.plot(xticks,df['condensed_t'], label='S223 with b-schema', linestyle='--', color = 'tab:orange')
plt.xlabel('Size of Model (1000s of Triples)')
plt.xticks(xticks[::2])
# plt.xticks(model_length, [f'{1+i} [{x}]' for i,x in enumerate(model_length)])
plt.legend()
plt.tight_layout()
# plt.show()
plt.savefig('query-time-both.png')
# %%

df = pd.read_csv('reasoning-time-s223.csv')
df_brick = pd.read_csv('reasoning-time-brick.csv')


xticks = [round(n/1000,1) for n in df['model_length']]
xticks_brick = [round(n/1000,1) for n in df_brick['model_length']]
plt.figure(figsize=(6,2))
plt.ylabel('Query Time (seconds)')
plt.plot(xticks_brick,df_brick['not_condensed_reasoning_t'], label='Brick', color = 'tab:blue')
plt.plot(xticks_brick,df_brick['condensed_reasoning_t'], label='Brick b-schema', color = 'tab:green')
plt.plot(xticks,df['not_condensed_reasoning_t'], label='S223', linestyle='--', color = 'tab:red')
plt.plot(xticks,df['condensed_reasoning_t'], label='S223 b-schema', linestyle='--', color = 'tab:orange')
plt.xlabel('Size of Model (1000s of Triples)')
plt.xticks(xticks[::2])
# plt.xticks(model_length, [f'{1+i} [{x}]' for i,x in enumerate(model_length)])
plt.legend()
plt.tight_layout()
# plt.show()
plt.savefig('reasoning-time-both.png')
# %%
