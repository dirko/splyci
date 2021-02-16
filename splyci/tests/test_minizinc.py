maxh = 31
maxw = 121

ncols = 20
nrows = 120

cells = []
for i in range(1,ncols):
    for j in range(1,nrows):
        cells.append((i, j))

left = [(i, i+1) for i in range(1,ncols-1)]
above = [(j, j+1) for j in range(1,nrows-1)]

temp = f'''
h={maxh};
w={maxw};

nleft={len(left) };
nabove={len(above) };
nincols={ncols+1};
ninrows={nrows+1};
ncolmatches=0;
ncells={len(cells)};

left=array2d(LEFT,POS,{[p for l in left for p in l]});
above=array2d(ABOVE,POS,{[p for a in above for p in a]});
col_matches=array2d(COLMATCHES,POS,[]);
row_matches=[];

cells_c = {[i for i, _ in cells]};
cells_r = {[j for _, j in cells]};
'''

print(temp)