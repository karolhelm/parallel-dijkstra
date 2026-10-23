#include <vector>
#include <iostream>
#include <climits>
#include <map>
#include <atomic>
//#include <omp.h>

using namespace std;

long long INF = LLONG_MAX;

struct edge{
    int v;
    int val;
};

struct node{
    int v;
    long long dist;
};

long long deltaStepping(vector<vector<edge>> &graph, long long delta){
    int n = graph.size();
    vector<vector<edge>> light(n), heavy(n);
    for(int u = 0; u < n; ++u){
        for(edge e : graph[u]){
            if(e.val > delta){
                heavy[u].push_back(e);
            }else{
                light[u].push_back(e);
            }
        }
    }

    vector<int> added(n, 0);
    vector<atomic<long long>> distance(n); 

    for(int i = 0; i<n; ++i){
        distance[i] = INF;
    }

    map<long long, vector<node>> buckets;

    auto relaxation = [&](edge e, node ne){
        long long newDist = ne.dist + e.val;
        
        #pragma omp critical(relaxation)
        { 
            long long oldDist = distance[e.v].load();
            if(newDist < oldDist){
                distance[e.v].store(newDist);
                buckets[newDist / delta].push_back({e.v, newDist});
            }
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

            vector<node> curBucket = move(it->second);   
            buckets.erase(it); 

            #pragma omp parallel for
            for(node curNode : curBucket){
                if(distance[curNode.v].load() != curNode.dist){
                    continue;
                }
                
                #pragma omp critical(heavy_pushback)
                if(added[curNode.v] == 0 && heavy[curNode.v].size() > 0){
                    heavyNodes.push_back(curNode);
                    added[curNode.v] = 1;
                }

                for(edge l : light[curNode.v]){
                    relaxation(l, curNode);
                }
            }
        }

        long long finalDistance = distance[n - 1].load();
        if(finalDistance != INF && finalDistance / delta == curIndex){
            return finalDistance;
        }

        #pragma omp parallel for
        for(node v : heavyNodes){
            long long distanceV = distance[v.v].load();

            for(edge h : heavy[v.v]){
                relaxation(h, {v.v, distanceV});
            }
        }
    }

    return distance[n - 1].load();
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
        
        long long w = 0;

        for(int i = 0; i < m; i++){
            int u, v, val;
            cin >> u >> v >> val;
            
            edge e;
            e.v = v;
            e.val = val;

            graph[u].push_back(e);
            w += val;
        }

        long long delta = max((long long)1, 2*w/m);
        long long answer = deltaStepping(graph, delta);

        if(answer == INF){
            cout << -1 << "\n";
        }else{
            cout << answer << "\n";
        }

        z--;
    }
}