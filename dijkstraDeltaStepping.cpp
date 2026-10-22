#include <vector>
#include <iostream>
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
    vector<int> added(n, 0);
    vector<long long> distance(n, INF); 
    map<long long, vector<node>> buckets;
    auto relaxation = [&](edge e, node ne){
        long long newDist = ne.dist + e.val;
        if(newDist < distance[e.v]){
            distance[e.v] = newDist;
            buckets[newDist / delta].push_back({e.v, newDist});
        }
    };
    distance[0] = 0;
    buckets[0].push_back({0, 0});
    while(!buckets.empty()){
        long long curIndex = buckets.begin()->first;
        vector<node> heavyNodes; 
        while(true){ 
            auto it = buckets.find(curIndex);
            if(it == buckets.end()){
                break;
            }
            vector<node> curBucket = std::move(it->second);   
            buckets.erase(it); 
            for(node curNode : curBucket){
                if (distance[curNode.v] != curNode.dist){
                    continue;
                }
                if(added[curNode.v] == 0 && heavy[curNode.v].size() > 0){
                    heavyNodes.push_back(curNode);
                    added[curNode.v] = 1;
                }
                for(edge l : light[curNode.v]){
                    relaxation(l, curNode);
                }
            }
        }
        if (distance[n - 1] != INF && distance[n - 1] / delta == curIndex){
            return distance[n - 1];
        }
        for(node v : heavyNodes){
            for(edge h : heavy[v.v]){
                relaxation(h, {v.v, distance[v.v]});
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
        if(answer == INF){
            cout << -1 << "\n";
        }else{
            cout << answer << "\n";
        }
        z--;
    }
}