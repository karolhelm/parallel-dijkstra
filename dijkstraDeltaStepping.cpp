#include <vector>
#include <iostream>
#include <queue>
#include <climits>
#include <map>

using namespace std;

long long INF = LLONG_MAX;

struct edge{
    int v;
    int val;
};
struct node
{
    int v;
    long long dist;
    bool operator<(const node& other) const {
        return dist > other.dist;
    }
};
long long deltaStepping(vector<vector<edge>> &graph, long long delta){
    int n = graph.size();
    vector<vector<edge>> light(n), heavy(n);
    for (int u = 0; u < n; u++){
        for (edge e : graph[u]){
            if(e.val > delta){
                heavy[u].push_back(e);
            }else{
                light[u].push_back(e);
            }
        }
    }
    vector<long long> distance(n, INF); 
    vector<char> recorded(n, 0);
    map<long long, vector<node>> buckets;
    distance[0] = 0;
    buckets[0].push_back({0, 0});
    while(!buckets.empty()){
        long long curIndex = buckets.begin()->first;
        while(true){
            auto it = buckets.find(curIndex);
            if(it == buckets.end()){
                break;
            }
            vector<node> curBucket = move(buckets[curIndex]);   
            buckets.erase(curIndex); 
            for(node act : curBucket){

            }
        }
    }
    return distance[n - 1];
}
// we want to go from 0 to n - 1 

int main(){
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int z;
    cin >> z;
    while(z > 0){
        int n;
        cin >> n;
        vector<vector<edge>> graph(n);
        int m;
        cin >> m;
        for(int i = 0; i < m; i++){
            int u, v, val;
            edge e;
            cin >> u >> v >> val;
            e.v = v;
            e.val = val;
            graph[u].push_back(e);
        }
        long long delta = 1;
        long long answer = deltaStepping(graph, delta);
        if(answer == LLONG_MAX){
            cout << -1 << "\n";
        }else{
            cout << answer << "\n";
        }
        z--;
    }
}