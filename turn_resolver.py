from game_logic import resolve_all_tasks, create_news
def run():
    results = resolve_all_tasks()
    if results:
        create_news('Turn resolved', '\n'.join(results))
    return results

if __name__ == '__main__':
    print('Resolving turn...')
    print(run())
