Introduct à la Reconoinace
de formes Statistiques

Schéma gireial

[Figure: diagram showing the flow: Observe -> Extraction caracteristiques -> Classifier -> Decision clasifict]

Obervat
On a $\vec{x} \in \mathbb{R}^n$, $\vec{x} = \begin{pmatrix} x_1 \\ \vdots \\ x_n \end{pmatrix}$ $\exists$ M classes $w_1, w_2, \dots, w_M$

Objectif: Détermin dans quelle classe norge $\vec{x}$

cal À partir de $\vec{x}$ $\Rightarrow$ Quell classe lui attribua

Méthodes déterministes

[Figure: Venn diagram of S, R1, R2, R3]

$\vec{x} \in S \subset \mathbb{R}^n$
$R = \bigcup_{n=1}^{M} R_n = S$ (exhaustivité)
$R_i \cap R_j = \emptyset$ si $i \neq j$ (non-ambiguité)

$\vec{x} \in R_m \Leftrightarrow \vec{x}$ ek dau la classe $w_m$

Voc: $M=2 \rightarrow$ "Detection" $\rightarrow$ "Discrimint"
$M > 2 \text{ mois conmu } \rightarrow$ "Classificat"

I. Méthodes Liscaines de Discrimination

A/ Cas à M= 2 classes

$\rightarrow$ Proklimatique: On a 2 basse d'exemples pou l'apprentissage
$B_{Am} = \{\vec{x} \mid \vec{x} \in w_1 \}$
$B_{AL} = \{ \vec{x} \mid \vec{x} \in w_2 \}$
$B_A = B_{A1} \cup B_{AL}$

à chaque the $B_A$ $\rightarrow$ $d^x = \begin{cases} +1 \text{ si } \vec{x} \in w_1 \\ -1 \text{ si } \vec{x} \in w_2 \end{cases}$

Objectif de la DL : detamion un vecteur $\vec{w} \in \mathbb{R}^N$ ta:

$\vec{w}^T \vec{x} > 0 \text{ si } \vec{x} \in w_1$
$\vec{w}^T \vec{x} < 0 \text{ si } \vec{x} \in w_2$

$\vec{w}^T \vec{x} = \sum w_i x_i =$ Produit scalaire entre $\vec{w}$ et $\vec{x}$

[Figure: graph of w^T x = 0]

$\vec{w}^T \vec{x} + w_0 = 0$: Eq d'1 Hyperplan. Notat: $\vec{w} = \begin{pmatrix} w_1 \\ \vdots \\ w_n \end{pmatrix}$, $\vec{x} = \begin{pmatrix} x_1 \\ \vdots \\ x_n \end{pmatrix}$

$\Rightarrow \vec{w}^T \vec{x} + w_0 = \vec{w}^T \vec{x'}$ $\rightarrow$ écriture + single

Somme dans la puite, on utilisera $\vec{w}$ et $\vec{x'}$ sans noter les "," i.e $\vec{w}^T \vec{x}$

Methodologic géminck: Base d'exemle $\rightarrow B_A$ cyprentissage (taille $P_A$)
$B_a$ girirdist (taille $P_B$)

B/ Methode de Helb

$J_{Helb} = \sum_{2=1}^{P_A} d_Q \vec{x}$

xquirendint: $\zeta_Q = \frac{1}{P_A} \sum \eta_Q$

Caractériset des performances:
P_A
$\text{To d'appenina : } \zeta_P = \frac{1}{P_A} \sum_Q m_Q$

$m_Q = \begin{cases} 1 \text{ si } \text{sign} (d_Q \vec{w}^T \vec{x} ) = \text{sign} (dd) \\ 0 \text{ sinon Emenn} \end{cases}$ pus d'enrein

C/ Methioch de la Pseudo- Inverse

*   Gritive plos rigoureN: errem quachatique

$J = \sum_{n=1}^{P_A} [w^T x^Q - d^Q]^2 = || \vec{d} - \vec{X} \vec{w} ||^2$
$d = \begin{pmatrix} d_1 \\ \vdots \\ d_{pA} \end{pmatrix}$
$\vec{X} = \begin{pmatrix} x_1^1 \dots x_1^n \\ \vdots \\ x_{pA}^1 \dots x_{pA}^n \end{pmatrix}$

Objectif: Trouva $\vec{w}$ qui minirise J

$J = [ \vec{d} - \vec{X} \vec{w} ] [ \vec{d} - \vec{X} \vec{w} ] = (\vec{d}^T \vec{d}) - \vec{d}^T \vec{X} \vec{w} - \vec{w}^T \vec{X}^T \vec{d} + \vec{w}^T \vec{X}^T \vec{X} \vec{w}$

$= a - 2 \vec{w}^T \vec{X}^T \vec{d} + \vec{w}^T \vec{X}^T \vec{X} \vec{w}$
$= a - 2 \vec{w}^T \vec{r} + \vec{w}^T M \vec{w} = a - 2 \sum w_i r_i + \sum w_i M_{ij} w_j$

$\frac{\partial J}{\partial w_m} = -2r_m + \sum M_{mj} w_j + \sum M_{im} w_i \text{ on } M_{ij} = M_{ji} \text{ ca } M^T = M$

$\frac{\partial J}{\partial w_m} = -2r_m + 2 \sum M_{mi} w_i$

dou $\frac{\partial J}{\partial w_m} = 0 \Rightarrow \sum M_{mi} w_i = r_m$

$\Rightarrow M \vec{w} = \vec{r}$

$\Rightarrow \vec{X}^T \vec{X} \vec{w} = \vec{X}^T \vec{d}$

Finelbst, on chuch $\vec{w}$ ty $\vec{X}^T \vec{X} \vec{w} = \vec{X}^T \vec{d}$

Scalet: + Cao 1: $\vec{X}^T \vec{X}$ ost inversibl. Allos $\vec{w} = (\vec{X}^T \vec{X})^{-1} \vec{X}^T \vec{d}$

[Figure: Pseudo inverse]

+ Cas 2: $\vec{X}^T \vec{X}$ non CM inversible

$M = \vec{X}^T \vec{X} \text{ est symtrique } \Rightarrow \text{ diagonalisable}$

i.e $\exists U \text{ normale } (U^T U = UU^T = Id) \text{ eq } M = UT \begin{pmatrix} \sigma_i & 0 \\ & \ddots \\ 0 & \sigma_n \end{pmatrix} U$

Soi't a le rong de M. Si R < N+1, M non invesitle (rang = nt de up non mil)

$M = U^T \begin{pmatrix} \sigma_i & 0 \\ & \ddots \\ 0 & \end{pmatrix} U$

Prender-inverse de M: $M^{PI} = U^T \begin{pmatrix} \frac{1}{\sigma_i} & 0 \\ & \ddots \\ 0 & \end{pmatrix} U$ On a bin $M^{PI} M = \vec{M}$

$ni \text{ rong } 1 = N+1$

$\vec{w} = (\vec{X}^T \vec{X})^{PI} \vec{X}^T \vec{d}$ : guminclint de la PI de $\vec{w}$

Exoyk: N=2
[Figure: graph of cluster points]
TP: Parfois quand $P_A \sim N$, il ya des di tren petit dore des coof to this grand.

Salat Aveputer talk for ove le hait

SD/ Limites de la PI
$J = \sum_Q (w^T x^Q - d_Q)^2$

En 1. Un I dan, $d_Q = 1$, $w^T x^Q = -1$

$(w^T x^Q - d_Q)^2 = 4 \text{ discriminat } Q$
•11=1 et $w^T x^Q = 3 \text{ dae } (w^T x^Q - d_Q)^2 = 4$

$\Rightarrow$ Le critère n'est pas le bon !

Il foudroit plutat utiliser:
$J = \sum_{Q=1}^{P_A} \text{sign} (w^T x^Q) - d_Q | miselt andytique ice cradiat$

Gritine du Perception: $J_P = \sum_{Q \in \Omega} -d_Q w^T x^Q$

dac, $J_P > 0$ et $J_P = 0 \text{ si aucure enein}$

Méthock Gradient : $\vec{w}^{+1} = \vec{w}^t + \delta |Q| \vec{V} J_P$

Algorithmre du Perception $\rightarrow$ converge vers me solut si $B_A$ est liviariant siparile

Sivon: problemes de convergence

Sdiscriminat logistique (Cox: 1980)

$g(x) = \frac{e^x}{1+e^x}$
Naveau onitore:
$J_{DL} = \sum_{Q=1}^{P_A} [d_Q - g(w^T x^Q)]^2$

→Fonet J dinvabl $\Rightarrow$ Mitchuck de prodient pour trouve $\omega$

Autre écitive de $\in$ tippe: $J_{DL} = \sum_Q [d_Q - \sigma(w^T x^Q)]^2$ où $\sigma(x) = \frac{e^{2x}-1}{e^{2x}+1} = 2g(x) -1$

[Figure: signmoid function]

Péreux de munus
